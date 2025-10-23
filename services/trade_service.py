import asyncio
from decimal import Decimal
import logging
import aiohttp
from web3 import Web3, AsyncWeb3
import websockets
import json
import traceback

from blockchain_config import get_contract_address, get_rpc_urls, get_subscription_method, get_ws_url
from state import State

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeService:
    def __init__(self, state=None, error_callback=None):
        self._last_block_number = None
        self.state = state if state is not None else State()
        self.pair_abi = json.load(open('./abis/pair_abi.json'))
        self.kfc_swap_abi = json.load(open('./abis/kfc_swap_abi.json'))
        self.error_callback = error_callback  # Callback для отправки ошибок пользователю
    
    async def _stop_block_monitoring(self):
        """Остановка мониторинга блоков"""
        self.block_monitoring = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Мониторинг блоков остановлен")

    async def _start_block_monitoring(self):
        """Запуск мониторинга новых блоков через WebSocket"""
        try:
            await self.state.start_block_monitoring()
            lp_state = await self.state.get_lp_state()
            network = lp_state['chain_name']
            
            # Проверяем, что сеть настроена
            if network is None:
                error_msg = "❌ Ошибка конфигурации: Сеть не определена!\n\n" \
                          f"chain_name: {network}\n" \
                          f"target_price: {lp_state['target_price']}\n" \
                          f"lp_address: {lp_state['lp']}\n\n" \
                          f"Чекер остановлен. Пожалуйста, настройте ликвидную пару через меню."
                
                logger.error(f"Network is None. chain_name:{network}, target_price:{lp_state['target_price']}, lp_address:{lp_state['lp']}")
                
                # Отправляем ошибку пользователю
                if self.error_callback:
                    await self.error_callback(error_msg)
                
                # Останавливаем мониторинг
                await self.state.stop_block_monitoring()
                return
            
            logger.info(f"Запуск мониторинга блоков для сети: {network}")
            
            # Получаем URL и метод подписки для выбранной сети
            ws_url = get_ws_url(network)
            if ws_url is None:
                error_msg = f"❌ Ошибка конфигурации: WebSocket URL не найден для сети '{network}'!\n\n" \
                          f"Чекер остановлен. Пожалуйста, проверьте настройки сети."
                
                logger.error(f"WebSocket URL not found for network: {network}")
                
                # Отправляем ошибку пользователю
                if self.error_callback:
                    await self.error_callback(error_msg)
                
                # Останавливаем мониторинг
                await self.state.stop_block_monitoring()
                return
                
            subscription_method = get_subscription_method(network)
            
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
                    if not await self.state.get_block_monitoring_state():
                        break
                    
                    try:
                        data = json.loads(message)
                        
                        # Проверяем, что это уведомление о новом блоке
                        if data.get("method") == "eth_subscription" and "params" in data:
                            block_data = data["params"]["result"]
                            
                            # Выводим информацию о новом блоке в консоль
                            block_number = int(block_data.get("number", "0x0"), 16)
                            timestamp = int(block_data.get("timestamp", "0x0"), 16)

                            pair_state = await self.state.get_lp_state()

                            if(pair_state['chain_name'] is not None and pair_state['target_price'] is not None and pair_state['lp'] is not None):
                                chain_name = pair_state["chain_name"]
                                target_price = pair_state['target_price']
                                lp_address = pair_state['lp']
                                await self.buy_token_v2(chain_name, target_price, lp_address)
                                
                                # print(f"\n🆕 НОВЫЙ БЛОК ОБНАРУЖЕН!")
                                # print(f"📊 Номер блока: {block_number}")
                                # print(f"⏰ Время: {timestamp}")
                                # print("-" * 50)
                            else:
                                error_msg = f"❌ Ошибка конфигурации: Ликвидная пара не настроена!\n\n" \
                                          f"chain_name: {pair_state['chain_name']}\n" \
                                          f"target_price: {pair_state['target_price']}\n" \
                                          f"lp_address: {pair_state['lp']}\n\n" \
                                          f"Чекер остановлен. Пожалуйста, настройте ликвидную пару через меню."
                                
                                logger.error(f"pair state is none. chain_name:{pair_state['chain_name']}, target_price:{pair_state['target_price']}, lp_address:{pair_state['lp']}")
                                
                                # Отправляем ошибку пользователю
                                if self.error_callback:
                                    await self.error_callback(error_msg)
                                
                                # Останавливаем мониторинг
                                await self.state.stop_block_monitoring()
                                break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Не удалось декодировать сообщение: {message}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке сообщения: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket соединение закрыто")
        except Exception as e:
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Ошибка в мониторинге блоков: {e}")
        finally:
            await self.state.stop_block_monitoring()
            self.websocket = None
            logger.info("Мониторинг блоков остановлен")

    async def buy_token_v2(self, chain_name, target_price, lp_address):
        try:
            rpc_urls= get_rpc_urls()
            w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_urls[chain_name]))
            pair_contarct = w3.eth.contract(address=w3.to_checksum_address(lp_address), abi=self.pair_abi)
            contarct_address = get_contract_address(chain_name)
            kfc_contarct = w3.eth.contract(address=w3.to_checksum_address(contarct_address),abi=self.kfc_swap_abi)
            
            token_0 = w3.to_checksum_address(await pair_contarct.functions.token0().call())
            token_1 = w3.to_checksum_address(await pair_contarct.functions.token1().call())
            target_price_usd = target_price

            path = [w3.to_checksum_address(token_0), w3.to_checksum_address(token_1)]
            pair_address = w3.to_checksum_address(contarct_address)
            eth_price_usd = await self.get_eth_price_usd_binance()
            target_price_eth = Decimal(target_price_usd) / eth_price_usd
            target_price_wei = int(target_price_eth * Decimal(1e18))
            print(pair_address, token_0, token_1, target_price)
            result = await kfc_contarct.functions.calculateEthToReachPrice(pair_address, token_0, token_1, target_price_wei).call()
            print(result)
        except Exception as error:
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise error


    async def get_eth_price_usd_binance(self):
        url = f"https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return Decimal(data['price'])
