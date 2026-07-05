import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.db import get_latest_ready_deployment, get_project_by_subdomain

app = FastAPI(title="DeployX Reverse Proxy")

_client = httpx.AsyncClient(follow_redirects=True, timeout=10.0)


def extract_subdomain(host_header: str) -> str | None:
    """'brave-zephyr-26b1.yourdomain.com:80' -> 'brave-zephyr-26b1'.
    Returns None for the bare root domain (no subdomain) or an unrelated host."""
    hostname = host_header.split(":")[0].lower()
    if not hostname.endswith(settings.root_domain):
        return None
    remainder = hostname[: -len(settings.root_domain)].rstrip(".")
    return remainder or None


@app.get("/{full_path:path}")
@app.head("/{full_path:path}")
async def proxy(request: Request, full_path: str):
    host_header = request.headers.get("host", "")
    subdomain = extract_subdomain(host_header)

    if not subdomain:
        return PlainTextResponse(
            "DeployX — point a project's subdomain here to view it.", status_code=200
        )

    project = get_project_by_subdomain(subdomain)
    if not project:
        return PlainTextResponse(f"No project found for '{subdomain}'", status_code=404)

    deployment = get_latest_ready_deployment(project["id"])
    if not deployment:
        return PlainTextResponse(
            f"'{project['name']}' has no successful deployment yet", status_code=404
        )

    # Root path serves index.html, same trick the original reverse proxy used.
    object_path = "index.html" if full_path in ("", "/") else full_path
    target_url = f"http://{settings.s3_website_endpoint}/__outputs/{project['id']}/{object_path}"

    upstream = await _client.get(target_url)

    excluded_headers = {"content-encoding", "transfer-encoding", "connection"}
    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in excluded_headers}

    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


@app.on_event("shutdown")
async def shutdown():
    await _client.aclose()
