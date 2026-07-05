from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Postgres
    database_url: str = "postgresql+psycopg://deployx:devpassword@localhost:5432/deployx"

    # ECS — values come straight out of `terraform output` on Day 1
    aws_region: str
    ecs_cluster: str
    ecs_task_definition: str
    ecs_subnet_id: str
    ecs_security_group_id: str
    ecs_container_name: str = "build-worker"

    # Used by the reverse proxy later; kept here so one .env covers everything
    s3_bucket: str = ""
    root_domain: str = "localhost"


settings = Settings()
