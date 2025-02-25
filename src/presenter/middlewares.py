import json
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Message, Update

from src.model.db import db_manager
from src.settings import LOGGER


async def transaction(
    handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: dict[str, Any],
) -> Any:
    async with db_manager.begin() as conn:
        await conn.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        data["conn"] = conn

        return await handler(event, data)


async def logging(
    handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
    event: Message,
    data: dict[str, Any],
) -> Any:
    LOGGER.debug("User %d sent: %s", event.from_user.id, event.text)

    return await handler(event, data)
