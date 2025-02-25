from typing import Any

from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError

from src.model.core import Service
from src.model.repositories import AsyncpgRepository
from src.model.weather_clients import (
    AccuWeatherClient,
    AggregatedWeatherClient,
    OpenWeatherMapClient,
)
from src.presenter.errors import AlreadyExistsError, ExternalError
from src.presenter.middlewares import logging, transaction
from src.presenter.schemas import (
    PydanticHistoryRecordShort,
    PydanticLocality,
    PydanticUser,
)
from src.presenter.states import WeatherRequest
from src.settings import LOGGER, api_settings
from src.view.core import View, FormattedView


dispatcher = Dispatcher(
    model=Service(
        AsyncpgRepository(),
        AggregatedWeatherClient(
            (
                AccuWeatherClient(api_settings.accuweather_key.get_secret_value()),
                OpenWeatherMapClient(
                    api_settings.openweathermap_key.get_secret_value()
                ),
            )
        ),
    ),
    view=FormattedView(),
)

dispatcher.update.outer_middleware(transaction)
dispatcher.message.outer_middleware(logging)


@dispatcher.message(StateFilter(None), CommandStart())
async def authenticate(message: Message, model: Service, view: View, conn: Any) -> None:
    try:
        await model.register(PydanticUser(**message.from_user.model_dump()), conn)
        await view.greet_new(message)
    except AlreadyExistsError:
        await view.greet_existent(message)


@dispatcher.message(Command("help"))
async def help_(message: Message, view: View) -> None:
    """
    Доступно даже во время других состояний, т.к. помощь может потребоваться в любой момент.
    """
    await view.help(message)


@dispatcher.message(StateFilter(None), Command("weather"))
async def request_locality(message: Message, view: View, state: FSMContext) -> None:
    await view.ask_locality(message)
    await state.set_state(WeatherRequest.locality)


@dispatcher.message(WeatherRequest.locality)
async def get_weather(
    message: Message, model: Service, view: View, conn: Any, state: FSMContext
) -> None:
    try:
        weather = await model.get_weather(
            PydanticLocality(user_id=message.from_user.id, name=message.text), conn
        )
    except ValidationError as exc:
        await view.tell_invalid_input(message)
        LOGGER.debug("Invalid input: %s", exc.errors())
    except ExternalError as exc:
        await view.tell_general_error(message)
        LOGGER.exception(exc)
    else:
        await view.show_weather(message, weather)
        await state.clear()


@dispatcher.message(StateFilter(None), Command("history"))
async def get_history(message: Message, model: Service, view: View, conn: Any) -> None:
    history = await model.get_history(
        PydanticHistoryRecordShort(user_id=message.from_user.id), conn
    )
    await view.show_history(message, history)


@dispatcher.message()
async def handle_unknown(message: Message, view: View) -> None:
    await view.tell_unknown(message)
