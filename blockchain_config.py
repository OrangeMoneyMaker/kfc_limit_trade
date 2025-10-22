"""
Конфигурация для подключения к различным блокчейн сетям
"""

# Конфигурация WebSocket URL для разных сетей
BLOCKCHAIN_WS_URLS = {
    "arbitrum": 'ws://65.108.192.118:8950'
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

def get_subscription_method(network: str) -> dict:
    """Получить метод подписки для указанной сети"""
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
