import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

if TYPE_CHECKING:
    from aiogram.types import Message

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096
SAFE_CHUNK_SIZE = 4000


def split_text(text: str, chunk_size: int = SAFE_CHUNK_SIZE) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


async def send_long_message(
    message: "Message",
    text: str,
    *,
    reply_markup=None,
    parse_mode: str = "HTML",
    chunk_size: int = SAFE_CHUNK_SIZE,
) -> None:
    parts = split_text(text, chunk_size)
    for i, part in enumerate(parts):
        kb = reply_markup if i == len(parts) - 1 else None
        await message.answer(part, reply_markup=kb, parse_mode=parse_mode)


async def safe_edit_text(message: "Message", text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        raise


def format_error(exc: Exception, max_len: int = 300) -> str:
    if isinstance(exc, RuntimeError):
        return str(exc)[:max_len]
    return str(exc)[:max_len]
