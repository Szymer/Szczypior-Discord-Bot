from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "szczypior-db-service"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_user: str | None = Field(default=None, alias="user")
    db_password: str | None = Field(default=None, alias="password")
    db_host: str | None = Field(default=None, alias="host")
    db_port: int | None = Field(default=None, alias="port")
    db_name: str | None = Field(default=None, alias="dbname")

    @cached_property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        required_fields = {
            "user": self.db_user,
            "password": self.db_password,
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_name,
        }
        missing_fields = [name for name, value in required_fields.items() if value in (None, "")]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"Missing database configuration. Set DATABASE_URL or all of: {missing}."
            )

        return URL.create(
            "postgresql+psycopg2",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": "require"},
        ).render_as_string(hide_password=False)


settings = Settings()
