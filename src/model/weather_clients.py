import asyncio
from abc import ABC, abstractmethod
from statistics import mean
from typing import Any

from httpx import AsyncClient, HTTPStatusError, RequestError

from src.presenter.errors import ExternalError
from src.presenter.schemas import (
    Locality,
    PydanticLocality,
    PydanticWeather,
    many_from_dict,
)


class WeatherClient(ABC):
    service: str

    weather_endpoint: str
    locality_endpoint: str

    def __init__(self, key: str, timeout: int = 10) -> None:
        self.key: str = key
        self.timeout: int = timeout

    async def _request(
        self, endpoint: str, session: AsyncClient, **kwargs
    ) -> list[dict[str, Any]]:
        try:
            response = await session.get(endpoint, timeout=self.timeout, **kwargs)
        except RequestError:
            raise ExternalError

        try:
            response.raise_for_status()
        except HTTPStatusError:
            raise ExternalError

        return response.json()

    @abstractmethod
    async def get(self, locality: Locality, session: Any) -> dict[str, Any]:
        pass


class AccuWeatherClient(WeatherClient):
    service = "AccuWeather"

    weather_endpoint = "http://dataservice.accuweather.com/currentconditions/v1"
    locality_endpoint = "http://dataservice.accuweather.com/locations/v1/cities/search"

    async def _get_locality_id(
        self, locality: PydanticLocality, session: AsyncClient
    ) -> str:
        body = await self._request(
            self.locality_endpoint,
            session,
            params={
                "apikey": self.key,
                "q": locality.name,
                "offset": 1,
            },
        )

        try:
            return body[0]["Key"]
        except IndexError:
            raise ExternalError

    async def _get_weather(self, id_: str, session: AsyncClient) -> dict[str, Any]:
        return (
            await self._request(
                f"{self.weather_endpoint}/{id_}",
                session,
                params={
                    "apikey": self.key,
                    "language": "ru-ru",
                    "details": True,
                },
            )
        )[0]

    async def get(
        self, locality: PydanticLocality, session: AsyncClient
    ) -> dict[str, Any]:
        id_ = await self._get_locality_id(locality, session)
        return await self._get_weather(id_, session)


class OpenWeatherMapClient(WeatherClient):
    service = "OpenWeatherMap"

    weather_endpoint = "https://api.openweathermap.org/data/2.5/weather"
    locality_endpoint = "https://api.openweathermap.org/geo/1.0/direct"

    async def _get_locality_coordinates(
        self, locality: PydanticLocality, session: AsyncClient
    ) -> tuple[float, float]:
        try:
            body = (
                await self._request(
                    self.locality_endpoint,
                    session,
                    params={
                        "q": locality.name,
                        "limit": "1",
                        "appid": self.key,
                    },
                )
            )[0]
        except IndexError:
            raise ExternalError

        return body["lat"], body["lon"]

    async def _get_weather(
        self, coordinates: tuple[float, float], session: AsyncClient
    ) -> dict[str, Any]:
        return await self._request(
            self.weather_endpoint,
            session,
            params={
                "lat": coordinates[0],
                "lon": coordinates[1],
                "appid": self.key,
                "units": "metric",
                "lang": "ru",
            },
        )

    async def get(
        self, locality: PydanticLocality, session: AsyncClient
    ) -> dict[str, Any]:
        coordinates = await self._get_locality_coordinates(locality, session)
        return await self._get_weather(coordinates, session)


class AggregatedWeatherClient:
    def __init__(self, clients: tuple[WeatherClient]) -> None:
        self.clients: tuple[WeatherClient] = clients

    @many_from_dict(PydanticWeather)
    async def _aggregate(
        self, locality: PydanticLocality, session: AsyncClient = AsyncClient()
    ) -> list[dict[str, Any]]:
        aggregation = await asyncio.gather(
            *(client.get(locality, session) for client in self.clients)
        )

        return [
            {"service": client.service, **weather}
            for client, weather in zip(self.clients, aggregation)
        ]

    @staticmethod
    def _compare(aggregation: list[PydanticWeather]) -> list[PydanticWeather]:
        aggregation.append(
            PydanticWeather(
                service="Среднее на основе всех служб",
                **{
                    field: mean(getattr(weather, field) for weather in aggregation)
                    for field in PydanticWeather.to_average
                },
            )
        )

        return aggregation

    async def get(self, locality: Locality) -> list[PydanticWeather]:
        aggregation = await self._aggregate(locality)

        return self._compare(aggregation)
