import logging
from typing import Annotated, Any

from pydantic import AfterValidator, PositiveFloat, PositiveInt, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


LOGGER: logging.Logger = logging.getLogger()


def _to_str(value: Any) -> str:
    return str(value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


class BotSettings(Settings):
    token: SecretStr
    pooling_timeout: PositiveInt = 10
    handle_as_tasks: bool = True
    allowed_updates: list[str] | None = None
    handle_signals: bool = True
    close_bot_session: bool = True


class APISettings(Settings):
    accuweather_key: SecretStr
    openweathermap_key: SecretStr


class DBSettings(Settings):
    dsn: Annotated[PostgresDsn, AfterValidator(_to_str)]
    min_size: PositiveInt = 10
    max_size: PositiveInt = 10
    max_queries: PositiveInt = 50000
    max_inactive_connection_lifetime: PositiveFloat = 300.0


bot_settings = BotSettings()  # type: ignore
api_settings = APISettings()  # type: ignore
db_settings = DBSettings()  # type: ignore
