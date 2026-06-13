import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import content, history, image_gen, start, text_ai, video_gen
from middleware.auth import AuthMiddleware, ThrottlingMiddleware
from services.http_client import close_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    dp.include_router(start.router)
    dp.include_router(text_ai.router)
    dp.include_router(image_gen.router)
    dp.include_router(video_gen.router)
    dp.include_router(content.router)
    dp.include_router(history.router)

    return dp


async def main() -> None:
    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = create_dispatcher()

    logger.info("🚀 ContentBot Pro started")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await close_client()
        await bot.session.close()
        logger.info("Bot stopped gracefully")


if __name__ == "__main__":
    asyncio.run(main())
