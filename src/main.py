"""
Точка входа в приложение.
"""

import asyncio
import logging

from aiogram import Bot

from src.model.db import db_manager
from src.presenter.core import dispatcher
from src.settings import bot_settings


async def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s — %(levelname)s: %(message)s"
    )
    bot = Bot(bot_settings.token.get_secret_value())

    async with db_manager:
        await dispatcher.start_polling(
            bot, **bot_settings.model_dump(exclude={"token"})
        )


if __name__ == "__main__":
    asyncio.run(main())
