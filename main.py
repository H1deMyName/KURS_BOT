import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import API_TOKEN
from database import init_db
from handlers import register_handlers

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    register_handlers(dp)

    init_db()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())