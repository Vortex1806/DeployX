"""Runs once per ECS Fargate task. Clones the target repo, builds it,
uploads the output to S3, and streams logs to Redis pub/sub the whole
way through — the direct Python equivalent of the original script.js.

Env vars, split into two groups:

Injected per-run by the api-server (see ecs_client.py containerOverrides):
    GIT_REPOSITORY_URL, PROJECT_ID, DEPLOYMENT_ID

Fixed in the task definition (see terraform/ecs.tf):
    S3_BUCKET, AWS_REGION, REDIS_HOST, REDIS_PORT,
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""
import mimetypes
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
import psycopg2
import redis

GIT_REPOSITORY_URL = os.environ["GIT_REPOSITORY_URL"]
PROJECT_ID = os.environ["PROJECT_ID"]
DEPLOYMENT_ID = os.environ["DEPLOYMENT_ID"]

S3_BUCKET = os.environ["S3_BUCKET"]
AWS_REGION = os.environ["AWS_REGION"]

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

OUTPUT_DIR = Path("/home/app/output")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
s3_client = boto3.client("s3", region_name=AWS_REGION)


def log(message: str) -> None:
    """Print to CloudWatch (via awslogs) and publish for anyone subscribed
    to this deployment's channel over the websocket gateway."""
    print(message, flush=True)
    try:
        redis_client.publish(f"logs:{DEPLOYMENT_ID}", message)
    except Exception as exc:  # noqa: BLE001 — never let a dead Redis kill the build
        print(f"[warn] failed to publish log to redis: {exc}", flush=True)


def set_deployment_status(status: str, error: str | None = None) -> None:
    """Write the final status straight to Postgres. The build-worker and
    the api-server share the same database, so this avoids needing an
    authenticated internal HTTP call between two trusted services."""
    with psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE deployment SET status = %s, error = %s, updated_at = %s WHERE id = %s",
                (status, error, datetime.now(timezone.utc), DEPLOYMENT_ID),
            )
        conn.commit()


def run_and_stream(command: list[str], cwd: Path) -> int:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in process.stdout:  # type: ignore[union-attr]
        log(line.rstrip())
    process.wait()
    return process.returncode


def upload_dist(dist_dir: Path) -> None:
    files = [p for p in dist_dir.rglob("*") if p.is_file()]
    log(f"Starting upload of {len(files)} files...")
    for path in files:
        key = f"__outputs/{PROJECT_ID}/{path.relative_to(dist_dir)}"
        content_type, _ = mimetypes.guess_type(str(path))
        log(f"uploading {path.relative_to(dist_dir)}")
        s3_client.upload_file(
            str(path),
            S3_BUCKET,
            key,
            ExtraArgs={"ContentType": content_type or "application/octet-stream"},
        )
    log("Upload complete.")


def main() -> int:
    log("Build Started...")

    clone_rc = subprocess.run(
        ["git", "clone", GIT_REPOSITORY_URL, str(OUTPUT_DIR)],
        capture_output=True,
        text=True,
    )
    if clone_rc.returncode != 0:
        log(f"git clone failed: {clone_rc.stderr}")
        set_deployment_status("FAILED", error="git clone failed")
        return 1
    log("Repository cloned.")

    install_rc = run_and_stream(["npm", "install"], cwd=OUTPUT_DIR)
    if install_rc != 0:
        set_deployment_status("FAILED", error="npm install failed")
        return 1

    build_rc = run_and_stream(["npm", "run", "build"], cwd=OUTPUT_DIR)
    if build_rc != 0:
        set_deployment_status("FAILED", error="npm run build failed")
        return 1
    log("Build Complete")

    dist_dir = OUTPUT_DIR / "dist"
    if not dist_dir.is_dir():
        log(f"error: expected build output at {dist_dir}, but it doesn't exist")
        set_deployment_status("FAILED", error="no dist/ directory produced by the build")
        return 1

    try:
        upload_dist(dist_dir)
    except Exception as exc:  # noqa: BLE001 — surface any S3 failure onto the deployment row
        log(f"error uploading to S3: {exc}")
        set_deployment_status("FAILED", error=str(exc))
        return 1

    log("Done")
    set_deployment_status("READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
