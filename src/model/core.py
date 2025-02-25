from typing import Any

from src.model.repositories import Repository
from src.model.weather_clients import AggregatedWeatherClient
from src.presenter.schemas import (
    PydanticHistoryRecord,
    PydanticHistoryRecordShort,
    PydanticLocality,
    PydanticUser,
    PydanticWeather,
)


class Service:
    def __init__(
        self, repository: Repository, weather_client: AggregatedWeatherClient
    ) -> None:
        self._repository = repository
        self._weather_client = weather_client

    async def register(self, user: PydanticUser, conn: Any) -> None:
        await self._repository.create_user(user, conn)

    async def get_weather(
        self, locality: PydanticLocality, conn: Any
    ) -> list[PydanticWeather]:
        comparison = await self._weather_client.get(locality)
        await self._repository.create_record(
            PydanticHistoryRecord(
                user_id=locality.user_id,
                locality=locality.name,
                weather=[weather.to_dict(exclude_none=True) for weather in comparison],
            ),
            conn,
        )

        return comparison

    async def get_history(
        self, history: PydanticHistoryRecordShort, conn: Any
    ) -> list[PydanticHistoryRecord]:
        return await self._repository.get_all_records(history, conn)
