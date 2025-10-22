"""
Настройка и конфигурация Telegram бота
"""
import asyncio
import logging
import websockets
import json
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from dotenv import load_dotenv
import os
from blockchain_config import get_ws_url, get_subscription_method, DEFAULT_CONFIG

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    """Класс для настройки и управления Telegram ботом"""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не найден в переменных окружения!")
        
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        self.block_monitoring = False
        self.websocket = None
        self.network = 'arbitrum'
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Обработчик команды /start
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            """Обработчик команды /start"""
            welcome_text = (
                "🤖 Добро пожаловать в KFC Limit Trade Bot!\n\n"
            )
            await message.answer(welcome_text, reply_markup=self._get_main_keyboard())
        
        # Обработчик кнопки "▶️ Старт мониторинг"
        @self.dp.message(lambda message: message.text == "▶️ Start")
        async def start_monitoring(message: Message):
            """Обработчик кнопки запуска мониторинга блоков"""
            if self.block_monitoring:
                await message.answer("⚠️ Мониторинг блоков уже запущен!")
                return
            
            await message.answer("🔄 Запускаю мониторинг блоков...")
            
            # Запускаем мониторинг в фоновом режиме
            asyncio.create_task(self._start_block_monitoring())
            
            await message.answer("✅ Мониторинг блоков запущен! Новые блоки будут отображаться в консоли.")
        
        # Обработчик кнопки "⏹️ Стоп мониторинг"
        @self.dp.message(lambda message: message.text == "⏹️ Stop")
        async def stop_monitoring(message: Message):
            """Обработчик кнопки остановки мониторинга блоков"""
            if not self.block_monitoring:
                await message.answer("⚠️ Мониторинг блоков не запущен!")
                return
            
            await message.answer("🔄 Останавливаю мониторинг блоков...")
            
            # Останавливаем мониторинг
            await self._stop_block_monitoring()
            
            await message.answer("✅ Мониторинг блоков остановлен!")
        
        # Обработчик неизвестных сообщений
        @self.dp.message()
        async def handle_unknown(message: Message):
            """Обработчик неизвестных сообщений"""
            await message.answer(
                "❓ Неизвестная команда. Используйте /help для получения справки.",
                reply_markup=self._get_main_keyboard()
            )
    
    def _get_main_keyboard(self):
        """Создает основную клавиатуру с кнопками"""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="▶️ Start"), KeyboardButton(text="⏹️ Stop")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        return keyboard
    
    async def _start_block_monitoring(self):
        """Запуск мониторинга новых блоков через WebSocket"""
        try:
            self.block_monitoring = True
            logger.info(f"Запуск мониторинга блоков для сети: {self.ws_network}")
            
            # Получаем URL и метод подписки для выбранной сети
            ws_url = get_ws_url(self.ws_network)
            subscription_method = get_subscription_method(self.ws_network)
            
            logger.info(f"Подключение к WebSocket: {ws_url}")
            
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                logger.info("WebSocket подключение установлено")
                
                # Подписываемся на новые блоки
                subscribe_message = {
                    "jsonrpc": "2.0",
                    "method": subscription_method["method"],
                    "params": subscription_method["params"],
                    "id": 1
                }
                
                await websocket.send(json.dumps(subscribe_message))
                logger.info("Подписка на новые блоки активирована")
                
                # Слушаем сообщения
                async for message in websocket:
                    if not self.block_monitoring:
                        break
                    
                    try:
                        data = json.loads(message)
                        
                        # Проверяем, что это уведомление о новом блоке
                        if data.get("method") == "eth_subscription" and "params" in data:
                            block_data = data["params"]["result"]
                            
                            # Выводим информацию о новом блоке в консоль
                            block_number = int(block_data.get("number", "0x0"), 16)
                            timestamp = int(block_data.get("timestamp", "0x0"), 16)
                            
                            print(f"\n🆕 НОВЫЙ БЛОК ОБНАРУЖЕН!")
                            print(f"📊 Номер блока: {block_number}")
                            print(f"⏰ Время: {timestamp}")
                            print("-" * 50)
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Не удалось декодировать сообщение: {message}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке сообщения: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket соединение закрыто")
        except Exception as e:
            logger.error(f"Ошибка в мониторинге блоков: {e}")
        finally:
            self.block_monitoring = False
            self.websocket = None
            logger.info("Мониторинг блоков остановлен")
    
    async def _stop_block_monitoring(self):
        """Остановка мониторинга блоков"""
        self.block_monitoring = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Мониторинг блоков остановлен")
    
    async def start_polling(self):
        """Запуск бота в режиме polling"""
        try:
            logger.info("Запуск бота...")
            
            # Удаляем webhook если он был установлен
            await self.bot.delete_webhook(drop_pending_updates=True)
            
            # Запускаем polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
        finally:
            # Останавливаем мониторинг при завершении работы бота
            if self.block_monitoring:
                await self._stop_block_monitoring()
            await self.bot.session.close()
            logger.info("Бот остановлен")
    
    async def stop(self):
        """Остановка бота"""
        # Останавливаем мониторинг
        if self.block_monitoring:
            await self._stop_block_monitoring()
        await self.bot.session.close()
        logger.info("Бот остановлен")
