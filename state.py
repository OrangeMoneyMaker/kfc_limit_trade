from web3 import Web3, AsyncWeb3
from blockchain_config import get_rpc_urls
from config import Config


class State:
    def __init__(self):
        self.current_lp = None
        self.lp_target_price = None
        self.chain_name = None
        self.waiting_for_lp_input = False
        self.block_monitoring = False
    
    async def start_block_monitoring(self):
        self.block_monitoring = True
        return self.block_monitoring
    
    async def stop_block_monitoring(self):
        self.block_monitoring = False
        return self.block_monitoring
    
    async def get_block_monitoring_state(self):
        return self.block_monitoring
    
    def get_network_by_address(self, address):
        try:
            rpc_urls = get_rpc_urls()
            checkseum_address = Web3.to_checksum_address(address)
            print(f"Поиск сети для адреса: {checkseum_address}")
            
            for network, rpc_url in rpc_urls.items():
                print(f"Проверка сети: {network} с RPC: {rpc_url}")
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if w3.is_connected():
                    print(f"Подключение к {network} успешно")
                    code = w3.eth.get_code(checkseum_address)
                    if code != b'':
                        print(f"Найдена сеть: {network}")
                        return network
                else:
                    print(f"Не удалось подключиться к {network}")
            
            print("Сеть не найдена, возвращаем 'Unknown'")
            return 'Unknown'
        except Exception as e:
            print(f"Ошибка при определении сети: {e}")
            return 'Unknown'
    
    async def get_lp_state(self):
        response = {
            "lp": self.current_lp,
            "target_price": self.lp_target_price,
            "chain_name": self.chain_name
        }
        print(f"Получено из состояния: lp={self.current_lp}, target_price={self.lp_target_price}, chain_name={self.chain_name}")
        return response
    
    def set_lp_state(self, lp: str, target_price: float):
        chain_name = self.get_network_by_address(Web3.to_checksum_address(lp))
        self.current_lp = lp
        self.lp_target_price = target_price
        self.chain_name = chain_name
        print(f"Сохранено в состояние: lp={lp}, target_price={target_price}, chain_name={chain_name}")