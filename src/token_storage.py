import logging
from .token import Token
from config import setup_logger


logger = setup_logger(name=__name__, log_file=__name__, level=logging.INFO)


class TokenStorage:
    def __init__(self):
        """
        Инициализация хранилища токенов.
        """
        self.tokens = {}

    def add_token(self, mint, creation_transaction):
        """
        Добавляет токен в хранилище.
        :param token: Экземпляр класса Token.
        """
        if mint in self.tokens:
            logger.info(f"Token with mint {mint} already exists.")
            return
        logger.debug(f"Token {mint} add")
        self.tokens[mint] = Token(creation_transaction)

    def get_token(self, mint):
        """
        Возвращает класс токен по mint.
        :param mint: Уникальный идентификатор токена (mint).
        :return: Экземпляр класса Token.
        """
        logger.debug(f"Token {mint} get_token")
        return self.tokens[mint]

    def remove_token(self, mint):
        """
        Удаляет токен из хранилища по mint.
        :param mint: Уникальный идентификатор токена (mint).
        """
        if mint in self.tokens:
            del self.tokens[mint]
            logger.debug(f"Token {mint} removed")
        else:
            raise ValueError(f"Token with mint {mint} not found.")

    def list_tokens(self):
        """
        Возвращает список всех токенов в хранилище.
        :return: Список экземпляров класса Token.
        """
        return list(self.tokens.values())

token_storage = TokenStorage()