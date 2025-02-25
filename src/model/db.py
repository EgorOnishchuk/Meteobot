from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any

from asyncpg import Connection, Pool, create_pool

from src.settings import db_settings


class DBManager(ABC):
    @asynccontextmanager
    @abstractmethod
    async def begin(self) -> AsyncGenerator[Connection, None]:
        pass

    @abstractmethod
    async def drop_tables(self) -> None:
        pass

    @abstractmethod
    async def __aenter__(self) -> None:
        pass

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


class AsyncpgManager(DBManager):
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings: dict[str, Any] = settings
        self.pool: Pool | None = None

    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[Connection, None]:
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    yield conn
        except AttributeError:
            raise ValueError("Pool is not initialized.")

    async def _create_tables(self) -> None:
        async with self.begin() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                first_name VARCHAR(64) NOT NULL
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id BIGINT NOT NULL,
                locality TEXT NOT NULL,
                weather JSONB,
                timestamp TIMESTAMP DEFAULT NOW()
                )
                """
            )

    async def drop_tables(self) -> None:
        async with self.begin() as conn:
            for table in ("users", "history"):
                await conn.execute(f"DROP TABLE IF EXISTS {table}")

    async def __aenter__(self) -> None:
        self.pool = await create_pool(**self.settings)
        await self._create_tables()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.pool.close()


db_manager: AsyncpgManager = AsyncpgManager(db_settings.model_dump())
