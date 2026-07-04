import boto3

from app.config import settings

_ecs = boto3.client("ecs", region_name=settings.aws_region)


def run_build_task(git_url: str, project_id: str, deployment_id: str) -> str:
    """Launch one Fargate task for this deployment. Returns the task ARN.

    Mirrors the original's RunTaskCommand almost exactly — same shape,
    boto3 instead of the JS SDK, containerOverrides carrying the
    per-deployment env vars into the otherwise-static task definition.
    """
    response = _ecs.run_task(
        cluster=settings.ecs_cluster,
        taskDefinition=settings.ecs_task_definition,
        launchType="FARGATE",
        count=1,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [settings.ecs_subnet_id],
                "securityGroups": [settings.ecs_security_group_id],
                "assignPublicIp": "ENABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": settings.ecs_container_name,
                    "environment": [
                        {"name": "GIT_REPOSITORY_URL", "value": git_url},
                        {"name": "PROJECT_ID", "value": project_id},
                        {"name": "DEPLOYMENT_ID", "value": deployment_id},
                    ],
                }
            ]
        },
    )

    failures = response.get("failures", [])
    if failures:
        raise RuntimeError(f"ECS RunTask failed: {failures}")

    return response["tasks"][0]["taskArn"]
