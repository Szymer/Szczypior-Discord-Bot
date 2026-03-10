from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "szczypior-db-service"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    database_url: str = Field(alias="DATABASE_URL")


settings = Settings()
