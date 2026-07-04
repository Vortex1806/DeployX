from fastapi import FastAPI

from app.routers import deployments, projects

app = FastAPI(title="DeployX API", version="0.1.0")

app.include_router(projects.router)
app.include_router(deployments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
