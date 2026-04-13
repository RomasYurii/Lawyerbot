import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import BOT_TOKEN
from app.handlers import common, client_flow, lawyer_flow
from app.database import async_session_maker
from app.database import init_models

from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from app.config import REDIS_URL


async def main():
    redis_client = Redis.from_url(REDIS_URL)
    # Створюємо сховище для Aiogram
    storage = RedisStorage(redis=redis_client)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

    dp = Dispatcher(storage=storage)
    dp["session_maker"] = async_session_maker
    dp.include_router(common.router)
    dp.include_router(client_flow.router)
    dp.include_router(lawyer_flow.router)

    print("Bot started.")

    print("Ініціалізація бази даних...")
    await init_models()
    print("Таблиці успішно створено (або вони вже існують)!")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())