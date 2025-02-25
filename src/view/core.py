from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from aiogram.types import Message
from aiogram.utils.formatting import Bold, Italic, Text, as_list

from src.presenter.schemas import (
    HistoryRecord,
    PydanticHistoryRecord,
    PydanticWeather,
    Weather,
)


def answer_one(
    func: Callable[["View", Message, Any], Text],
) -> Callable[["View", Message, Any], Text]:
    async def wrapper(self, message: Message, *args: Any, **kwargs: Any) -> None:
        content = func(self, message, *args, **kwargs)
        await message.answer(**content.as_kwargs())

    return wrapper


def answer_many(
    func: Callable[["View", Message, Any], Iterable[Text]],
) -> Callable[["View", Message, Any], Iterable[Text]]:
    async def wrapper(self, message: Message, *args: Any, **kwargs: Any) -> None:
        content = func(self, message, *args, **kwargs)

        for portion in content:
            await message.answer(**portion.as_kwargs())

    return wrapper


class View(ABC):
    @abstractmethod
    def greet_new(self, message: Message) -> Any:
        pass

    @abstractmethod
    def greet_existent(self, message: Message) -> Any:
        pass

    @abstractmethod
    def help(self, message: Message) -> Any:
        pass

    @abstractmethod
    def ask_locality(self, message: Message) -> Any:
        pass

    @abstractmethod
    def show_weather(self, message: Message, weather: list[Weather]) -> Any:
        pass

    @abstractmethod
    def show_history(self, message: Message, history: list[HistoryRecord]) -> Any:
        pass

    @abstractmethod
    def tell_invalid_input(self, message: Message) -> Any:
        pass

    @abstractmethod
    def tell_general_error(self, message: Message) -> Any:
        pass

    @abstractmethod
    def tell_unknown(self, message: Message) -> Any:
        pass


class FormattedView(View):
    @staticmethod
    def _greet(message: Message, additional: tuple[str | Text]) -> Text:
        return Text("Привет, ", Bold(message.from_user.first_name), "! ", *additional)

    @answer_one
    def greet_new(self, message: Message) -> Text:
        return self._greet(
            message,
            (
                "Рад с тобой познакомиться! Чтобы узнать больше о том, что я умею, введи ",
                Italic("/help"),
                ".",
            ),
        )

    @answer_one
    def greet_existent(self, message: Message) -> Text:
        return self._greet(message, ("Рад снова тебя видеть!",))

    @answer_one
    def help(self, message: Message) -> Text:
        return as_list(
            "Вот что я умею.",
            *[
                f"{marker} {command} — {description}."
                for marker, command, description in (
                    ("👋", "/start", "Представиться системе и начать общение"),
                    ("❓", "/help", "Показать список команд (это сообщение)"),
                    (
                        "☀️",
                        "/weather",
                        "Определить текущее состояние погоды на основе сопоставления данных от нескольких "
                        "метеослужб",
                    ),
                    ("📃", "/history", "Вывести историю погодных запросов"),
                )
            ],
        )

    @answer_one
    def ask_locality(self, message: Message) -> Text:
        return Text(
            "Введи ",
            Bold("название населённого пункта России"),
            ", погоду в котором хочешь узнать.",
        )

    @staticmethod
    def _render_list(pairs: dict[str, Any]) -> Text:
        return as_list(*(f"{param}: {value}" for param, value in pairs.items()))

    @answer_many
    def show_weather(
        self, message: Message, comparison: list[PydanticWeather]
    ) -> Iterator[Text]:
        return (
            self._render_list(weather.to_dict(by_alias=True, exclude_none=True))
            for weather in comparison
        )

    @answer_many
    def show_history(
        self, message: Message, history: list[PydanticHistoryRecord]
    ) -> Iterator[Text]:
        if not history:
            return iter(
                (
                    Text(
                        "Ты ещё не сравнивал погоду. Самое время это исправить — введи ",
                        Italic("/weather"),
                        "!",
                    ),
                )
            )
        return (
            Text(
                Bold(record.locality),
                ", ",
                Italic(record.timestamp.strftime("%d.%m.%Y %H:%M")),
                "\n",
                as_list(
                    *(self._render_list(weather) for weather in record.weather),
                    sep="\n" * 2,
                ),
            )
            for record in history
        )

    @answer_one
    def tell_invalid_input(self, message: Message) -> Text:
        return Text(
            "К сожалению, я тебя не понял. Убедись, что вводишь всё правильно и попробуй ещё раз."
        )

    @answer_one
    def tell_general_error(self, message: Message) -> Text:
        return Text(
            "К сожалению, я не смог обработать твой запрос. Пожалуйста, попробуй позже."
        )

    @answer_one
    def tell_unknown(self, message: Message) -> Text:
        return Text(
            "К сожалению, я тебя не понимаю. Чтобы узнать, что я умею, введи ",
            Italic("/help"),
            ".",
        )
