import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import API_TOKEN
from database import init_db, populate_exercises
from handlers import register_handlers

async def main():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    # Инициализация бота и диспетчера
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # Регистрация обработчиков
    register_handlers(dp)

    # Инициализация и заполнение базы данных
    init_db()
    populate_exercises()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
