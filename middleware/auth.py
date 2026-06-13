import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import config
from utils.texts import ACCESS_DENIED

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = _extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        if not config.is_allowed(user_id):
            await _deny_access(event)
            return None

        return await handler(event, data)


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float | None = None):
        self.rate_limit = rate_limit or config.THROTTLE_RATE
        self._last_request: dict[int, float] = {}
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = _extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        async with self._locks[user_id]:
            now = time.monotonic()
            elapsed = now - self._last_request.get(user_id, 0)
            if elapsed < self.rate_limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Подожди секунду...", show_alert=False)
                return None
            self._last_request[user_id] = now

        return await handler(event, data)


def _extract_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message) and event.from_user:
        return event.from_user.id
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user.id
    return None


async def _deny_access(event: TelegramObject) -> None:
    if isinstance(event, Message):
        await event.answer(ACCESS_DENIED)
    elif isinstance(event, CallbackQuery):
        await event.answer(ACCESS_DENIED, show_alert=True)
