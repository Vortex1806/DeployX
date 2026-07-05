from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "deployx"
    postgres_user: str = "deployx"
    postgres_password: str

    # e.g. deployx-outputs-86ed24.s3-website.ap-south-1.amazonaws.com
    # (from `terraform output s3_website_endpoint`)
    s3_website_endpoint: str

    # e.g. yourdomain.com — used to strip the subdomain off the Host header
    root_domain: str


settings = Settings()
