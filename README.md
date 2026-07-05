# DeployX

A from-scratch, Python/FastAPI rewrite of the Vercel-clone build ("Vortex Deploy"),
running on free-tier AWS: one EC2 box for the always-on services, ECS Fargate
for ephemeral build tasks, S3 static website hosting for output — no EKS,
no RDS/ElastiCache, no CloudFront/Route53.

## Repo layout

```
deployx/
  terraform/              infra: ECS cluster, ECR, S3, EC2, security groups, IAM
  ec2/
    docker-compose.yml     runs on the EC2 host: postgres, redis (+ api-server, reverse-proxy later)
    user_data.sh            cloud-init: installs docker on first boot
  docker-compose.dev.yml   local-only postgres+redis for building the api-server on your laptop
  api-server/              (next) FastAPI app
  build-worker/            (next) the container ECS runs per deployment
  reverse-proxy/           (next) subdomain -> S3 website router
```

## Day 1, hour 0-1: stand up the infra

1. `cd terraform`
2. `cp terraform.tfvars.example terraform.tfvars` and fill in:
   - `key_pair_name` — an EC2 key pair that already exists in `ap-south-1` (create one in the console under EC2 > Key Pairs if you don't have one — you'll need the downloaded `.pem` to SSH in)
   - `postgres_password` — pick a real value. This gets baked into the build-worker's ECS task definition as a plaintext env var (see the NOTE in `ecs.tf` — fine for now, flagged for the hardening pass later) so the build-worker can write deployment status straight to Postgres.

   > **Already applied this before today?** `postgres_password` is a new
   > required variable — add it to your existing `terraform.tfvars` and run
   > `terraform apply` again. It only touches the ECS task definition (new
   > revision) and an output; your EC2 instance won't be recreated. Then SSH
   > into the box, update `/opt/deployx/.env` so `POSTGRES_PASSWORD` matches
   > the same value, and `sudo docker compose up -d` to restart Postgres with it.

   SSH (port 22) is open to `0.0.0.0/0` since your IP moves around — key-pair auth is
   the actual gate. Worth adding `fail2ban` on the box at some point (`sudo apt install
   fail2ban`) to cut down on brute-force noise in the logs, but not urgent for a 2-day build.
3. `terraform init`
4. `terraform plan` — read through it, this is the whole footprint of the project
5. `terraform apply`
6. Note the outputs: `ec2_public_ip`, `s3_website_endpoint`, `ecr_repository_url`, `ecs_cluster_name`, `ecs_task_definition_arn`, `ecs_subnet_id`, `ecs_tasks_security_group_id` — the api-server's `.env` will need most of these.

## Day 1, hour 1-2: get docker-compose running on the box

```
scp -i /path/to/your-key.pem ec2/docker-compose.yml ubuntu@<ec2_public_ip>:/opt/deployx/
ssh -i /path/to/your-key.pem ubuntu@<ec2_public_ip>
cd /opt/deployx
echo "POSTGRES_PASSWORD=<pick-something>" > .env
sudo docker compose up -d
sudo docker compose ps    # confirm postgres + redis are up
```

Cloud-init takes 30-60s to finish installing docker after the instance first boots —
if `docker` isn't found yet, wait a bit and retry.

## Day 1, hour 2-4: api-server

```
cd api-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `DATABASE_URL` — leave as-is if you're testing locally against `docker-compose.dev.yml`
- `AWS_REGION`, `ECS_CLUSTER`, `ECS_TASK_DEFINITION`, `ECS_SUBNET_ID`, `ECS_SECURITY_GROUP_ID` — straight from `terraform output` in `terraform/`
- `S3_BUCKET`, `ROOT_DOMAIN` — not used yet, needed by the reverse proxy tomorrow

Bring up local Postgres + Redis and run the migration:

```
cd ..
docker compose -f docker-compose.dev.yml up -d
cd api-server
alembic upgrade head
```

Run it:

```
uvicorn app.main:app --reload
```

Then hit `http://localhost:8000/docs` and try it end to end:

```
curl -X POST localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my-test-site", "git_url": "https://github.com/some-user/some-static-repo"}'

# copy the returned "id", then:
curl -X POST localhost:8000/projects/<project_id>/deploy
```

If your AWS credentials are configured (`aws configure` or env vars) and the ECS
values in `.env` are correct, this actually launches a Fargate task right now —
check the ECS console or `aws ecs list-tasks --cluster deployx-cluster`. The
build-worker image doesn't exist in ECR yet (that's hour 4-6), so the task will
fail to pull the image — that's expected at this stage. A `FAILED` deployment
row with a real ECS task ARN attached means the trigger wiring is correct.

## Day 1, hour 4-6: build-worker

Build the image:

```
cd build-worker
docker build -t deployx-build-worker .
```

**Test it locally first**, against your local dev Postgres/Redis, before pushing
anywhere — much faster feedback loop than round-tripping through ECS:

```
cd ..
docker compose -f docker-compose.dev.yml up -d   # postgres + redis, if not already up

docker run --rm --network host \
  -e GIT_REPOSITORY_URL=https://github.com/<some-user>/<some-small-static-repo> \
  -e PROJECT_ID=test-project \
  -e DEPLOYMENT_ID=<a-real-deployment-id-from-your-postgres-so-the-status-update-works> \
  -e S3_BUCKET=<your-s3-bucket-name-from-terraform-output> \
  -e AWS_REGION=ap-south-1 \
  -e REDIS_HOST=localhost -e REDIS_PORT=6379 \
  -e POSTGRES_HOST=localhost -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=deployx -e POSTGRES_USER=deployx -e POSTGRES_PASSWORD=devpassword \
  -e AWS_ACCESS_KEY_ID=<yours> -e AWS_SECRET_ACCESS_KEY=<yours> \
  deployx-build-worker
```

`--network host` only works cleanly on Linux; on Windows/Mac Docker Desktop use
`-e REDIS_HOST=host.docker.internal -e POSTGRES_HOST=host.docker.internal`
instead of `--network host`, and drop that flag.

Watch the logs print live, confirm files land in the S3 bucket
(`aws s3 ls s3://<bucket>/__outputs/test-project/`), and confirm the
deployment row's `status` flips to `READY` (`GET /deployments/{id}` on the
api-server).

**Push to ECR** once that works:

```
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com

docker tag deployx-build-worker:latest <ecr_repository_url-from-terraform-output>:latest
docker push <ecr_repository_url-from-terraform-output>:latest
```

Then re-run the real end-to-end test from hour 2-4 (`POST /projects/{id}/deploy`)
— this time the ECS task should actually pull the image, run, and finish with
`READY` and real files in S3.

Note: at this point `api-server` should be running on the EC2 box itself
(not your laptop) so it shares one Postgres with the build-worker — see the
scp + venv steps you already ran. Everything below assumes that's the case.

## Day 2, hour 0-2: reverse proxy + your domain

Copy it to the box:

```
scp -i your-key.pem -r reverse-proxy ubuntu@<ec2_public_ip>:/opt/deployx/reverse-proxy
```

SSH in, add the two new variables the reverse-proxy needs to `/opt/deployx/.env`
(same file docker-compose already reads `POSTGRES_PASSWORD` from):

```
echo "S3_WEBSITE_ENDPOINT=<from terraform output, e.g. deployx-outputs-86ed24.s3-website.ap-south-1.amazonaws.com>" >> /opt/deployx/.env
echo "ROOT_DOMAIN=yourdomain.com" >> /opt/deployx/.env
```

Then:

```
cd /opt/deployx
sudo docker compose up -d --build reverse-proxy
sudo docker compose logs -f reverse-proxy   # confirm it started cleanly, ctrl-C to stop tailing
```

**Test it before touching DNS at all**, by faking the Host header — this proves
the whole lookup chain (subdomain → project → deployment → S3) works,
independent of anything domain-related:

```
curl -H "Host: <your-project-slug>.yourdomain.com" http://<ec2_public_ip>/
curl -H "Host: <your-project-slug>.yourdomain.com" http://<ec2_public_ip>/assets/index-Dsh4kXul.js
```

The first should return real HTML, the second real JS — no more 404s, because
the proxy is now rewriting `/assets/...` into the correct `__outputs/<project_id>/assets/...`
S3 path before forwarding.

**Once that works, wire up DNS** at your domain registrar:
- `A` record: `@` → `<ec2_public_ip>` (Elastic IP, so it won't change)
- `A` record: `*` → `<ec2_public_ip>` (wildcard — catches every project's subdomain)

DNS can take a few minutes to propagate. Once it does:

```
http://<your-project-slug>.yourdomain.com
```

should load the real site directly — no more Host header spoofing needed, and
no more raw S3 URL.

## Cost / cleanup

Everything here fits free tier (EC2 t3.micro, ECS Fargate billed per-second only
while a build runs, S3, ECR). Don't `terraform destroy` between sessions — it
throws away the Elastic IP association, the Postgres data, and the api-server
setup on the box, none of which need to go anywhere. If you want to save the
few cents of idle EC2 cost overnight, `aws ec2 stop-instances` / `start-instances`
instead — same Elastic IP, same disk, same everything, just paused.
