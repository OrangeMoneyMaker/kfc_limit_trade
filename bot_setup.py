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
from config import Config
from services.trade_service import TradeService
from state import State

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
        self.state = State()
        self.trade_service = TradeService(state=self.state, error_callback=self._send_error_message)
        self.config = Config()
        self.websocket = None
        self.network = 'arbitrum'
        self.active_chat_id = None  # Храним ID активного чата
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Обработчик команды /start
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            """Обработчик команды /start"""
            # Сохраняем chat_id для отправки ошибок
            self.active_chat_id = message.chat.id
            welcome_text = (
                "🤖 Добро пожаловать в KFC Limit Trade Bot!\n\n"
            )
            await message.answer(welcome_text, reply_markup=self._get_main_keyboard())
        
        # Обработчик кнопки "▶️ Start"
        @self.dp.message(lambda message: message.text == "▶️ Start")
        async def start_monitoring(message: Message):
            """Обработчик кнопки запуска мониторинга блоков"""
            # Сохраняем chat_id для отправки ошибок
            self.active_chat_id = message.chat.id
            
            if await self.state.get_block_monitoring_state():
                await message.answer("⚠️ Мониторинг блоков уже запущен!")
                return
            
            # Проверяем, что ликвидная пара настроена
            lp_state = await self.state.get_lp_state()
            if not lp_state['lp'] or not lp_state['target_price'] or not lp_state['chain_name']:
                await message.answer(
                    "❌ Ликвидная пара не настроена!\n\n"
                    "Пожалуйста, сначала настройте ликвидную пару через кнопку 'Добавить ликвид пару'.",
                    reply_markup=self._get_main_keyboard()
                )
                return
            
            await message.answer("🔄 Запускаю мониторинг блоков...")
            
            # Запускаем мониторинг в фоновом режиме
            if self.trade_service:
                asyncio.create_task(self.trade_service._start_block_monitoring())
            else:
                await message.answer("❌ Ошибка инициализации сервиса торговли!")
            
            await message.answer("✅ Мониторинг блоков запущен! Новые блоки будут отображаться в консоли.")
        
        # Обработчик кнопки "⏹️ Stop"
        @self.dp.message(lambda message: message.text == "⏹️ Stop")
        async def stop_monitoring(message: Message):
            """Обработчик кнопки остановки мониторинга блоков"""
            if await self.state.get_block_monitoring_state():
                await message.answer("⚠️ Мониторинг блоков не запущен!")
                return
            
            await message.answer("🔄 Останавливаю мониторинг блоков...")
            
            # Останавливаем мониторинг
            if self.trade_service:
                await self.trade_service._stop_block_monitoring()
            else:
                await message.answer("❌ Ошибка инициализации сервиса торговли!")
            
            await message.answer("✅ Мониторинг блоков остановлен!")

        # Обработчик кнопки "Добавить ликвид пару"
        @self.dp.message(lambda message: message.text == "Добавить ликвид пару")
        async def add_liquidity_pair(message: Message):
            """Обработчик кнопки добавления ликвидной пары"""
            await message.answer(
                "💧 Введите адрес ликвидной пары и целевую цену через пробел.\n\n"
                "Формат: <адрес_контракта> <цена>\n"
                "Примеры:\n"
                "• 0x1234...abcd 2500.50 (стандартный адрес)\n"
                "• 0xaaa1...5e 2500.50 (Uniswap V4 и др.)\n\n"
                "Или нажмите 'Отмена' для возврата в главное меню.",
                reply_markup=self._get_cancel_keyboard()
            )
            # Устанавливаем состояние ожидания ввода
            self.state.waiting_for_lp_input = True

        # Обработчик кнопки "Текущая пара"
        @self.dp.message(lambda message: message.text == "Текущая пара")
        async def show_current_pair(message: Message):
            """Обработчик кнопки показа текущей пары"""
            lp_state = await self.state.get_lp_state()
            if lp_state['lp'] and lp_state['target_price']:
                await message.answer(
                    f"📊 Адрес контракта ликвидной пары: {lp_state['lp']}\n"
                    f"🎯 Целевая цена: {lp_state['target_price']}\n"
                    f"Сеть: {lp_state['chain_name']}",
                    reply_markup=self._get_main_keyboard()
                )
            else:
                await message.answer(
                    "❌ Ликвидная пара не установлена.\n"
                    "Используйте кнопку 'Добавить ликвид пару' для настройки.",
                    reply_markup=self._get_main_keyboard()
                )
        
        # Обработчик кнопки "Отмена"
        @self.dp.message(lambda message: message.text == "Отмена")
        async def cancel_input(message: Message):
            """Обработчик кнопки отмены"""
            self.state.waiting_for_lp_input = False
            await message.answer(
                "❌ Ввод отменен. Возвращаемся в главное меню.",
                reply_markup=self._get_main_keyboard()
            )

        @self.dp.message(lambda message: message.text == "Информация о контрактах.")
        async def show_all_contracts(message: Message):
            self.state.waiting_for_lp_input = False
            contracts = await self.config.get_available_contracts()

            if not contracts:
                # Удаляем промежуточное сообщение (если хотим) и отправляем, что нет контрактов
                await message.answer(
                    "ℹ️ Контракты не найдены.",
                    reply_markup=self._get_main_keyboard()
                )
                return

            lines = []
            for c in contracts:
                chain = c.get("chain_name", "<неизвестная сеть>")
                addr = c.get("address_contract", "<нет адреса>")
                # подчёркивание, чтобы при копировании точно скопировалось
                # Используем моноширинный шрифт (```) или inline-код (`) для удобства копирования
                lines.append(f"**{chain.capitalize()}**: `{addr}`")

            message_text = "📄 Доступные контракты:\n\n" + "\n".join(lines)

            await message.answer(
                message_text,
                parse_mode='Markdown',
                reply_markup=self._get_main_keyboard()
            )

        
        # Обработчик ввода ликвидной пары и цены
        @self.dp.message()
        async def handle_lp_input(message: Message):
            """Обработчик ввода ликвидной пары и цены"""
            # Проверяем, ожидаем ли мы ввод ликвидной пары
            if hasattr(self.state, 'waiting_for_lp_input') and self.state.waiting_for_lp_input:
                try:
                    # Парсим введенную строку
                    parts = message.text.strip().split()
                    if len(parts) != 2:
                        await message.answer(
                            "❌ Неверный формат! Введите в формате: <адрес_контракта> <цена>\n"
                            "Пример: 0x1234...abcd 2500.50",
                            reply_markup=self._get_cancel_keyboard()
                        )
                        return
                    
                    lp_address = parts[0]
                    target_price = float(parts[1])
                    
                    # Валидация адреса контракта (должен начинаться с 0x и быть валидной длины)
                    if not lp_address.startswith('0x'):
                        await message.answer(
                            "❌ Неверный формат адреса! Адрес должен начинаться с '0x'.\n"
                            "Пример: 0x1234567890abcdef1234567890abcdef12345678",
                            reply_markup=self._get_cancel_keyboard()
                        )
                        return
                    
                    # Проверяем, что адрес содержит только валидные hex символы
                    hex_part = lp_address[2:]  # Убираем '0x'
                    if not all(c in '0123456789abcdefABCDEF' for c in hex_part):
                        await message.answer(
                            "❌ Неверный формат адреса! Адрес должен содержать только hex символы.\n"
                            "Пример: 0x1234567890abcdef1234567890abcdef12345678",
                            reply_markup=self._get_cancel_keyboard()
                        )
                        return
                    
                    # Проверяем минимальную длину (минимум 40 символов для стандартного адреса)
                    if len(hex_part) < 40:
                        await message.answer(
                            "❌ Адрес слишком короткий! Минимальная длина: 40 символов после '0x'.\n"
                            "Пример: 0x1234567890abcdef1234567890abcdef12345678",
                            reply_markup=self._get_cancel_keyboard()
                        )
                        return
                    
                    # Валидация цены (должна быть положительной)
                    if target_price <= 0:
                        await message.answer(
                            "❌ Цена должна быть положительным числом!",
                            reply_markup=self._get_cancel_keyboard()
                        )
                        return
                    
                    # Сохраняем данные в состояние
                    self.state.set_lp_state(lp_address, target_price)
                    self.state.waiting_for_lp_input = False
                    
                    # Получаем сохраненные данные для отображения
                    lp_state = await self.state.get_lp_state()
                    await message.answer(
                        f"✅ Ликвидная пара успешно добавлена!\n\n"
                        f"📊 Адрес контракта: {lp_address}\n"
                        f"🎯 Целевая цена: {target_price}\n"
                        f"Сеть: {lp_state['chain_name']}",
                        reply_markup=self._get_main_keyboard()
                    )
                    
                except ValueError:
                    await message.answer(
                        "❌ Неверный формат цены! Введите число с плавающей точкой.\n"
                        "Пример: 2500.50",
                        reply_markup=self._get_cancel_keyboard()
                    )
                except Exception as e:
                    await message.answer(
                        f"❌ Ошибка при обработке данных: {str(e)}",
                        reply_markup=self._get_cancel_keyboard()
                    )
            else:
                return

    def _get_main_keyboard(self):
        """Создает основную клавиатуру с кнопками"""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Информация о контрактах.")],
                [KeyboardButton(text="Добавить ликвид пару")],
                [KeyboardButton(text="Текущая пара")],
                [KeyboardButton(text="▶️ Start"), KeyboardButton(text="⏹️ Stop")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        return keyboard
    
    def _get_cancel_keyboard(self):
        """Создает клавиатуру с кнопкой отмены"""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        return keyboard
    
    async def _send_error_message(self, error_message: str):
        """Отправляет сообщение об ошибке пользователю"""
        try:
            if self.active_chat_id:
                await self.bot.send_message(chat_id=self.active_chat_id, text=error_message)
                logger.info(f"Ошибка отправлена пользователю в чат {self.active_chat_id}")
            else:
                logger.error(f"Ошибка в TradeService (нет активного чата): {error_message}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")
    
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
            if await self.state.get_block_monitoring_state():
                await self._stop_block_monitoring()
            await self.bot.session.close()
            logger.info("Бот остановлен")
    
    async def stop(self):
        """Остановка бота"""
        # Останавливаем мониторинг
        if await self.state.get_block_monitoring_state():
            await self._stop_block_monitoring()
        await self.bot.session.close()
        logger.info("Бот остановлен")
