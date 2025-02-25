from abc import ABC, abstractmethod
from typing import Any

from asyncpg import Connection, Record, UniqueViolationError

from src.presenter.errors import AlreadyExistsError
from src.presenter.schemas import (
    HistoryRecordShort,
    PydanticHistoryRecord,
    PydanticHistoryRecordShort,
    PydanticUser,
    User,
    UserShort,
    many_from_dict,
)


class Repository(ABC):
    @abstractmethod
    async def create_user(self, user: User, conn: Any) -> None:
        pass

    @abstractmethod
    async def get_all_records(
        self, history: HistoryRecordShort, conn: Any
    ) -> list[Any]:
        pass

    @abstractmethod
    async def create_record(self, history: UserShort, conn: Any) -> None:
        pass


class AsyncpgRepository(Repository):
    async def create_user(self, user: PydanticUser, conn: Connection) -> None:
        try:
            await conn.execute("INSERT INTO users VALUES ($1, $2)", *user.to_tuple())
        except UniqueViolationError:
            raise AlreadyExistsError

    @many_from_dict(PydanticHistoryRecord)
    async def get_all_records(
        self, history: PydanticHistoryRecordShort, conn: Connection
    ) -> list[Record]:
        return await conn.fetch(
            "SELECT * FROM history WHERE user_id = $1", *history.to_tuple()
        )

    async def create_record(
        self, history: PydanticHistoryRecord, conn: Connection
    ) -> None:
        await conn.execute(
            "INSERT INTO history (user_id, locality, weather) VALUES ($1, $2, $3)",
            *history.to_tuple(exclude_none=True),
        )
