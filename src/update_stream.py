import asyncio
import json
import logging
from .token_storage import token_storage

from websocket_client import ws_client
from config import setup_logger


logger = setup_logger(name=__name__, log_file=__name__, level=logging.INFO)


async def subscribe_token_trade(token_address):
    """Подписывается на торговые события для конкретного токена."""
    payload = {
        "method": "subscribeTokenTrade",
        "keys": [token_address]
    }
    websocket = await ws_client.connect()
    await websocket.send(json.dumps(payload))
    logger.debug(f"Подписались на торговые события для токена: {token_address}")


async def unsubscribe_token_trade(token_address):
    """Отписывается на торговые события для конкретного токена."""
    payload = {
        "method": "unsubscribeTokenTrade",
        "keys": [token_address]
    }
    await asyncio.sleep(4)
    websocket = await ws_client.connect()
    await websocket.send(json.dumps(payload))
    logger.debug(f"Отписались от торговых событий для токена: {token_address}")
    token_storage.remove_token(token_address)


async def subscribe_new_token():
    """Подписываемся на события создания новых токенов"""
    payload = {
        "method": "subscribeNewToken",
    }
    websocket = await ws_client.connect()
    await websocket.send(json.dumps(payload))
    logger.debug("Подписались на события создания новых токенов.")


async def unsubscribe_new_token():
    """Отписываемся от событий создания новых токенов"""
    payload = {
        "method": "unsubscribeNewToken",
    }
    websocket = await ws_client.connect()
    await websocket.send(json.dumps(payload))
    logger.debug("Отписались от событий создания новых токенов.")