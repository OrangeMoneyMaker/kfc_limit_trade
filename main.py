"""
Главный файл для запуска Telegram бота
"""
import asyncio
import logging
from bot_setup import TelegramBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для запуска бота"""
    bot = None
    try:
        # Создаем экземпляр бота
        bot = TelegramBot()
        
        # Запускаем бота
        await bot.start_polling()
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if bot:
            await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
