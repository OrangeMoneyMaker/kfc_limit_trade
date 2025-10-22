import asyncio
import aiohttp

class TradeService:
    def __init__(self,rpc_url: str, poll_interval: float = 5.0):
        self.rpc_url = rpc_url
        self.poll_interval = poll_interval
        self._last_block_number = None
    
    async def _get_latest_block_number(self) -> int:
        # пример запроса к RPC‑эндпоинту Ethereum‑совместимой сети
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            async with session.post(self.rpc_url, json=payload) as resp:
                resp_json = await resp.json()
                # результат приходит в hex‑формате, например "0x10d4f"
                block_number_hex = resp_json.get("result")
                if block_number_hex is None:
                    raise RuntimeError("Не удалось получить номер блока")
                return int(block_number_hex, 16)
            
    async def waiting_new_block(self):
        try:
            # Инициализируем _last_block_number
            self._last_block_number = await self._get_latest_block_number()
            print(f"Стартовое значение блока: {self._last_block_number}")
            # Бесконечный цикл опроса
            while True:
                await asyncio.sleep(self.poll_interval)
                current = await self._get_latest_block_number()
                if current > self._last_block_number:
                    # найден новый(ые) блок(и)
                    print(f"Новый блок обнаружен! Был {self._last_block_number}, стал {current}")
                    self._last_block_number = current
        except Exception as error:
            raise error