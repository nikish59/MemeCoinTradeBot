import asyncio
import ssl
import aiohttp
import time
import logging
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.commitment_config import CommitmentLevel
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig
from asyncio import Queue
from config.config import trade_config
from dataclasses import dataclass
from typing import List, Optional


from config import setup_logger


logger = setup_logger(name=__name__, log_file=__name__, level=logging.INFO)



@dataclass
class TradeResult:
    time: int  # Unix timestamp
    action: str
    mint: str
    amount: float
    tx_signature: Optional[str]
    response_content: Optional[str]


class TokenTradingAPI:
    trade_api_url = "https://pumpportal.fun/api/trade-local"  # URL для API торговли
    rpc_endpoint_url = "https://api.mainnet-beta.solana.com/"  # RPC-эндпоинт
    trades_result: List[TradeResult] = []

    def __init__(self, trade_queue: Queue):
        self.config = trade_config
        self.trade_queue = trade_queue
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def _make_transaction(self, url, payload, session):
        """
        Отправляет запрос на выполнение транзакции (покупка или продажа).
        
        """
        logger.debug(f"Отправка запроса на {url} с данными {payload}")
        try:
            async with session.post(url, json=payload, ssl=self.ssl_context) as response:
                if response.status == 200:
                    logger.info(f"Успешный ответ от {url}")
                    return await response.read()
                else:
                    logger.error(f"Ошибка при выполнении запроса: {response.status}")
                    return None
        except Exception as e:
            logger.exception(f"Исключение при выполнении запроса: {e}")
            return None

    async def _process_transaction(self, response_content, mint, action, amount, session):
        """
        Обрабатывает транзакцию и обновляет состояние токенов.
        
        """
        logger.debug(f"Обработка транзакции для {mint} с действием {action}")
        keypair = Keypair.from_base58_string(self.config.get("private_key"))
        tx = VersionedTransaction(VersionedTransaction.from_bytes(response_content).message, [keypair])
        commitment = CommitmentLevel.Confirmed
        cfg = RpcSendTransactionConfig(preflight_commitment=commitment)
        try:
            async with session.post(
                url=self.rpc_endpoint_url,
                headers={"Content-Type": "application/json"},
                data=SendVersionedTransaction(tx, cfg).to_json(),
                ssl=self.ssl_context
            ) as rpc_response:
                if rpc_response.status == 200:
                    rpc_res = await rpc_response.json()
                    tx_signature = rpc_res.get('result')
                    if tx_signature:
                        logger.info(f"Транзакция {action} успешно выполнена: https://solscan.io/tx/{tx_signature}")
                        return tx_signature
                    else:
                        logger.error(f"Транзакция {action} не выполнена: {rpc_res}, токен {mint}")
                else:
                    logger.error(f"Ошибка выполнения RPC-запроса: {rpc_response.status}")
        except Exception as e:
            logger.exception(f"Исключение при обработке транзакции: {e}, {response_content}, {mint}, {action}")

    async def buy_or_sell(self, mint, amount, action):
        """
        Объединенная функция для покупки и продажи токена.
        
        :param mint: Номер токена.
        :param amount: Количество токена для транзакции.
        :param action: Действие для транзакции (покупка/продажа).
    
        """
        logger.debug(f"Начало операции {action} для {mint} на сумму {amount}")
        payload = {
            "publicKey": self.config.get("public_key"),
            "action": action,
            "mint": mint,
            "amount": amount,
            "denominatedInSol": "false",
            "slippage": self.config.get("slippage"),
            "priorityFee": self.config.get("priority_fee"),
            "pool": "pump"
        }
        async with aiohttp.ClientSession() as session:
            response_content = await self._make_transaction(self.trade_api_url, payload, session)
            if response_content:
                tx_signature = await self._process_transaction(response_content, mint, action, amount, session)
        self.trade_queue.task_done()
        self.trades_result.append(
            TradeResult(time=int(time.time()), action=action, mint=mint, amount=amount,
                        tx_signature=tx_signature, response_content=response_content))

    async def trade_worker(self):
        """
        Фоновый процесс для обработки очереди торгов.
        
        """
        while True:
            mint, amount, action = await self.trade_queue.get()
            logger.info(f"Получена задача: {action} {mint} на сумму {amount}")
            await self.buy_or_sell(mint, amount, action)


    async def start(self):
        """
        Запускает фоновый процесс.
        
        """
        logger.info("Запуск фонового процесса торговли")
        asyncio.create_task(self.trade_worker())
