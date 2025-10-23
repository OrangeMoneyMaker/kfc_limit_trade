"""
Конфигурация для подключения к различным блокчейн сетям
"""

# Конфигурация WebSocket URL для разных сетей
BLOCKCHAIN_WS_URLS = {
    "arbitrum": 'ws://65.108.192.118:8950'
}

CONTRACTS_IN_CHAINS = {
    "arbitrum": "0x895D855a02946E736E493ff44b46a236f77C0C72",
    "ethereum": "0x895D855a02946E736E493ff44b46a236f77C0C72",
    "base": "0x895D855a02946E736E493ff44b46a236f77C0C72"
}

# Методы подписки для разных сетей
SUBSCRIPTION_METHODS = {
    "ethereum": {
        "method": "eth_subscribe",
        "params": ["newHeads"]
    },
    "polygon": {
        "method": "eth_subscribe", 
        "params": ["newHeads"]
    },
    "arbitrum": {
        "method": "eth_subscribe",
        "params": ["newHeads"]
    },
    "optimism": {
        "method": "eth_subscribe",
        "params": ["newHeads"]
    },
    "binance_smart_chain": {
        "method": "eth_subscribe",
        "params": ["newHeads"]
    },
    "avalanche": {
        "method": "eth_subscribe",
        "params": ["newHeads"]
    },
    "fantom": {
        "method": "eth_subscribe",
        "params": ["newHeads"]
    }
}

# Настройки по умолчанию
DEFAULT_CONFIG = {
    "network": "ethereum_mainnet",
    "reconnect_interval": 5,  # секунды
    "max_reconnect_attempts": 10,
    "timeout": 30,  # секунды
    "log_level": "INFO"
}

def get_ws_url(network: str) -> str:
    """Получить WebSocket URL для указанной сети"""
    return BLOCKCHAIN_WS_URLS.get(network)

def get_contract_address(chain_name: str) -> str:
    try:
        return CONTRACTS_IN_CHAINS[chain_name]
    except KeyError:
        raise Exception(f"Сеть '{chain_name}' не поддерживается.")
    
def get_rpc_urls():
    return {
         "arbitrum": 'http://65.108.192.118:8949',
         "ethereum": "http://65.108.233.239:7545",
         "base": "http://65.108.192.118:5545"
    }

def get_subscription_method(network: str) -> dict:
    """Получить метод подписки для указанной сети"""
    # Проверяем, что network не None
    if network is None:
        raise ValueError("Network не может быть None")
    
    # Определяем тип сети по названию
    if "ethereum" in network.lower():
        return SUBSCRIPTION_METHODS["ethereum"]
    elif "polygon" in network.lower():
        return SUBSCRIPTION_METHODS["polygon"]
    elif "arbitrum" in network.lower():
        return SUBSCRIPTION_METHODS["arbitrum"]
    elif "optimism" in network.lower():
        return SUBSCRIPTION_METHODS["optimism"]
    elif "bsc" in network.lower() or "binance" in network.lower():
        return SUBSCRIPTION_METHODS["binance_smart_chain"]
    elif "avalanche" in network.lower() or "avax" in network.lower():
        return SUBSCRIPTION_METHODS["avalanche"]
    elif "fantom" in network.lower():
        return SUBSCRIPTION_METHODS["fantom"]
    else:
        return SUBSCRIPTION_METHODS["ethereum"]  # По умолчанию Ethereum
