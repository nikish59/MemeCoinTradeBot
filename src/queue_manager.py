import asyncio
import logging
from asyncio import Queue

from config import setup_logger
logger = setup_logger(name=__name__, log_file=__name__, level=logging.INFO)


# Создаем очередь
trade_queue = Queue()

async def add_trade_to_queue(mint, amount, action):
    """
    Функция для добавления задачи в очередь.
    
    :param mint: Номер токена.
    :param amount: Количество токена для транзакции.
    :param action: Действие для транзакции (покупка/продажа).
    
    """
    await trade_queue.put((mint, amount, action))
    logger.info(f"Добавлена задача: {action} {amount} для {mint}")
