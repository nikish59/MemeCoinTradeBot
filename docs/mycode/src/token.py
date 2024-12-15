import asyncio
import time
import logging
import aiohttp
from .queue_manager import add_trade_to_queue
from config.config import token_config, trade_config
from config import setup_logger


logger = setup_logger(name=__name__, log_file=__name__, level=logging.INFO)


class Token:

    def __init__(self, creation_transaction):
        """
        Инициализация токена. Сохраняется информация о токене, время создания и конфигурация импульса.
        """
        self.history_transaction = []
        self.my_transaction = []
        self.buyers = set()  # Хранение уникальных покупателей
        self.inactive_task_flag = True
        self.buy_flag = False
        self.price_per_purchased_token = None
        self.price_per_sold_token = None
        self.add_transaction(creation_transaction)
        self.mint = creation_transaction["mint"]
        self.url = creation_transaction["uri"]
        self.creation_time = int(time.time())
        self.sell_multiplier = trade_config["sell_multiplier"]
        self.amount = trade_config["amount"]
        self.total_sols = 0
        logger.debug(f"Token {self.mint} created with initial transaction {creation_transaction}")
        asyncio.create_task(self.check_social_activity())


    async def check_social_activity(self):
        """
        Функция для проверки социальных сетей
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url, ssl=False) as response:  # Отключаем SSL-проверку
                    if response.status == 200:
                        data = await response.json()
                        fields = ["twitter", "telegram", "website"]
                        missing_fields = [field for field in fields if field not in data]

                        if not missing_fields:
                            logger.debug(f"All required fields are present: {fields}")
                            self.sell_multiplier = trade_config["sell_multiplier_with_social_activity"]
                            return True
                    else:
                        logger.error(f"Request failed with status {response.status} for token {self.mint}")
                        return False
            except Exception as e:
                logger.error(f"Error checking social activity for token {self.mint}: {e}")
                return False

    def add_transaction(self, transaction):
        """
        Добавление новой транзакции в историю токена.
        """
        transaction_with_timestamp = {
            **transaction,
            "time": int(time.time())
        }
        self.history_transaction.append(transaction_with_timestamp)

        # добавляем информацию, если мы покупали
        if transaction["traderPublicKey"] == trade_config["public_key"]:
            self.my_transaction.append(transaction_with_timestamp)
            if transaction["txType"] == "buy":
                self.buy_flag = True
                # Рассчитываем цену одного купленного токена
                self.price_per_purchased_token = transaction["vSolInBondingCurve"] / transaction[
                    "vTokensInBondingCurve"]
                self.inactive_task_flag = True
                logger.info(f"Price per purchased token: {self.price_per_purchased_token}")
            elif transaction["txType"] == "sell":
                # Рассчитываем цену одного проданного токена
                self.price_per_sold_token = transaction["vSolInBondingCurve"] / transaction["vTokensInBondingCurve"]
                logger.info(
                    f"Price per sold token: {self.price_per_sold_token}, profit: {self.price_per_sold_token - self.price_per_purchased_token}")
                from src.update_stream import unsubscribe_token_trade
                asyncio.create_task(unsubscribe_token_trade(token_address=self.mint))

        # Добавление уникального покупателя, если тип транзакции - "buy"
        if transaction["txType"] == "buy":
            self.buyers.add(transaction["traderPublicKey"])
        

    def control_actions(self, transaction):

        # проверяем были ли ранее сделки с этим токеном и не вополняются ли транзакции по нему сейчас
        if self.my_transaction and self.inactive_task_flag:
            price_for_last_transaction = transaction["vSolInBondingCurve"] / transaction["vTokensInBondingCurve"]
            if self.sell_multiplier > price_for_last_transaction / self.price_per_purchased_token:
                self.inactive_task_flag = False
                asyncio.create_task(add_trade_to_queue(self.mint, self.amount, "sell"))

        # проверяем есть ли импульс у токена после совершения min_transactions
        elif len(self.history_transaction) == token_config["min_transactions"]:
            if self.has_momentum():
                logger.info(f"Token {self.mint} has momentum! Initiating buy.")
                self.inactive_task_flag = False
                #asyncio.create_task(add_trade_to_queue(self.mint, self.amount, "buy"))
            else:
                logger.info(f"Token {self.mint} does not have momentum. Unsubscribing.")
                from src.update_stream import unsubscribe_token_trade
                asyncio.create_task(unsubscribe_token_trade(token_address=self.mint))

    def has_momentum(self) -> bool:
        """
        Проверяет, есть ли у токена импульс.
        """
        time_since_creation = time.time() - self.history_transaction[0]["time"]
        if time_since_creation < token_config["time_window"] and len(self.buyers) >= token_config["min_buyers"]:
            return True
        else:
            return False

    def strategy(self, transaction):
        """
        Простая стратегия.
        """
        activity = asyncio.create_task(self.check_social_activity())
        if transaction["txType"] == "buy":
            self.total_sols += int(transaction["vSolInBondingCurve"]) / int(transaction["vTokensInBondingCurve"]) * int(transaction["tokenAmount"])
        elif transaction["txType"] == "sell":
            self.total_sols -= int(transaction["vSolInBondingCurve"]) / int(transaction["vTokensInBondingCurve"]) * int(transaction["tokenAmount"])
        if activity and self.inactive_task_flag and self.total_sols > 10:
            logger.info(f"Token {self.mint} {self.total_sols}SOL and has social networks. Initiating buy.")
            self.inactive_task_flag = False
            asyncio.create_task(add_trade_to_queue(self.mint, self.amount, "buy"))
        
        elif self.buy_flag and transaction["vSolInBondingCurve"] / transaction["vTokensInBondingCurve"] / self.price_per_purchased_token > 2.5:
            logger.info(f"Price went up 2.5x. Initiating sell.")
            asyncio.create_task(add_trade_to_queue(self.mint, self.amount, "sell"))
        elif self.buy_flag and transaction["vSolInBondingCurve"] / transaction["vTokensInBondingCurve"] / self.price_per_purchased_token < 0.85:
            logger.info(f"Price went down 15%. Initiating sell.")
            asyncio.create_task(add_trade_to_queue(self.mint, self.amount, "sell"))

    def process_transaction(self, transaction):
        """
        Обрабатывает транзакцию: добавляет в историю и решает что делать с токеном.
        """
        #self.control_actions(transaction)
        if transaction["txType"] in ["buy", "sell"]:
            self.strategy(transaction)
        self.add_transaction(transaction)