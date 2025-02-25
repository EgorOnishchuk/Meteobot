from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import wraps
from typing import Annotated, Any, ClassVar, TypeVar
from uuid import UUID

from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class Schema(ABC):
    @abstractmethod
    def to_dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def to_tuple(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        pass


class PydanticSchema(BaseModel, Schema):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    def to_dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.model_dump(*args, **kwargs)

    def to_tuple(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        return tuple(self.to_dict(*args, **kwargs).values())


class UserShort(Schema):
    id: Any


class PydanticUserShort(PydanticSchema, UserShort):
    id: int


class User(UserShort):
    first_name: Any


class PydanticUser(PydanticUserShort, User):
    """
    Информация о мин. и макс. длине имени предположительная: в документации Telegram ограничения не раскрываются.
    """

    first_name: Annotated[str, Field(min_length=1, max_length=64)]


class HistoryRecordShort(Schema):
    user_id: Any


class PydanticHistoryRecordShort(PydanticSchema, HistoryRecordShort):
    user_id: int


class HistoryRecord(HistoryRecordShort):
    id: Any
    locality: Any
    weather: Any
    timestamp: Any


class PydanticHistoryRecord(PydanticHistoryRecordShort, HistoryRecord):
    id: UUID | None = None
    locality: str
    weather: list[dict[str, Any]]
    timestamp: datetime | None = None


class Locality(Schema):
    name: Any
    user_id: Any


class PydanticLocality(PydanticSchema, Locality):
    name: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"[А-ЯЁ][а-яё]+(?:[- ][А-ЯЁ][а-яё]+)*(?:-на-[А-ЯЁ][а-яё]+)?$",
            alias="locality",
        ),
    ]
    user_id: int


class Weather(Schema):
    summary: Any
    real_temperature: Any
    feels_like_temperature: Any
    atmospheric_pressure: Any
    wind_speed: Any
    cloudiness: Any
    humidity: Any


class PydanticWeather(PydanticSchema, Weather):
    to_average: ClassVar[set[str]] = {
        "real_temperature",
        "feels_like_temperature",
        "atmospheric_pressure",
        "wind_speed",
        "cloudiness",
        "humidity",
    }

    service: Annotated[str, Field(min_length=1, serialization_alias="Метеослужба")]
    summary: Annotated[
        str | None,
        Field(
            min_length=1,
            validation_alias=AliasChoices(
                "WeatherText",
                AliasPath("weather", 0, "description"),
            ),
            serialization_alias="Краткий итог",
        ),
    ] = None

    real_temperature: Annotated[
        float,
        Field(
            validation_alias=AliasChoices(
                AliasPath("Temperature", "Metric", "Value"),
                AliasPath("main", "temp"),
            ),
            serialization_alias="Температура, ℃",
        ),
    ]
    feels_like_temperature: Annotated[
        float,
        Field(
            validation_alias=AliasChoices(
                AliasPath("RealFeelTemperature", "Metric", "Value"),
                AliasPath("main", "feels_like"),
            ),
            serialization_alias="Ощущаемая температура, ℃",
        ),
    ]
    atmospheric_pressure: Annotated[
        float,
        Field(
            validation_alias=AliasChoices(
                AliasPath("Pressure", "Metric", "Value"),
                AliasPath("main", "pressure"),
            ),
            serialization_alias="Атмосферное давление, мм рт. ст.",
        ),
    ]
    wind_speed: Annotated[
        float,
        Field(
            validation_alias=AliasChoices(
                AliasPath("Wind", "Speed", "Metric", "Value"),
                AliasPath("wind", "speed"),
            ),
            serialization_alias="Скорость ветра, м/с",
        ),
    ]
    cloudiness: Annotated[
        float,
        Field(
            ge=0,
            le=100,
            validation_alias=AliasChoices(
                "CloudCover",
                AliasPath("clouds", "all"),
            ),
            serialization_alias="Облачность, %",
        ),
    ]
    humidity: Annotated[
        float,
        Field(
            ge=0,
            le=100,
            validation_alias=AliasChoices(
                "RelativeHumidity",
                AliasPath("main", "humidity"),
            ),
            serialization_alias="Влажность, %",
        ),
    ]

    @field_validator("summary")
    @classmethod
    def capitalize(cls, value: str) -> str:
        return value.capitalize()

    @field_validator(*to_average)
    @classmethod
    def round(cls, value: float) -> float:
        return round(value, 1)


SchemaT = TypeVar("SchemaT", bound=Schema)
FuncT = TypeVar("FuncT", bound=Callable[..., Awaitable[Any]])


def many_from_dict(dto_class: type[SchemaT]) -> Callable[[FuncT], FuncT]:
    def decorator(func: FuncT) -> FuncT:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> list[SchemaT]:
            objs = await func(self, *args, **kwargs)

            return [dto_class(**dict(obj)) for obj in objs]

        return wrapper

    return decorator
