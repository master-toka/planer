import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from database import init_db
from handlers import router
from scheduler import TaskScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создание бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаем роутер с обработчиками
    dp.include_router(router)
    
    # Инициализация планировщика
    scheduler = TaskScheduler(bot)
    scheduler.start()
    logger.info("Планировщик задач запущен")
    
    # Сохраняем планировщик в данные бота для доступа в хендлерах
    bot.scheduler = scheduler
    
    # Запуск бота
    try:
        logger.info("Бот начал polling")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())