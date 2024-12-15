import asyncio
import json
import logging
import time

import websockets

from config import handle_messages_config, setup_logger
from websocket_client import ws_client  # Импортируем экземпляр WebSocket клиента
from src import (
    token_storage,
    unsubscribe_new_token,
    subscribe_new_token,
    subscribe_token_trade,
    TokenTradingAPI,
    trade_queue,
    add_trade_to_queue
)

logger = setup_logger("main", "main.log", logging.INFO)


async def handle_messages(websocket):
    """Обрабатывает входящие сообщения и подписывается на торговлю токенами при создании нового токена."""
    token_creation_count = 0
    await subscribe_new_token()

    while True:
        try:
            # Ожидаем сообщение с тайм-аутом
            message = await asyncio.wait_for(websocket.recv(), timeout=handle_messages_config["timeout_duration"])
            message_data = json.loads(message)
            logger.debug(f"Получено сообщение: {message}")

            if message_data.get("txType") == "create":
                if token_creation_count >= handle_messages_config["max_tokens"]:
                    logger.info("Достигнут лимит по созданным токенам. Прекращаем подписку.")
                    asyncio.create_task(unsubscribe_new_token())
                    pass
                else:
                    token_creation_count += 1
                    token_address = message_data["mint"]
                    asyncio.create_task(subscribe_token_trade(token_address=token_address))
                    token_storage.add_token(mint=token_address, creation_transaction=message_data)

            elif message_data.get("txType") in ["sell", "buy"]:
                token_address = message_data.get("mint")
                token = token_storage.get_token(token_address)
                token.process_transaction(message_data)

        except asyncio.TimeoutError:
            # Если тайм-аут истек
            logger.info(
                f"Тайм-аут истек: не было сообщений в течение {handle_messages_config["timeout_duration"]}секунд.")
            # продаем оставшиеся токены в сесиии
            for token in token_storage.list_tokens():
                await add_trade_to_queue(token.mint, token.amount, "sell")
            await websocket.close()
            break

        except asyncio.CancelledError:
            logger.exception("Ожидание было отменено")
            raise Exception  # Пробрасываем исключение для логики выше

        except websockets.ConnectionClosed:
            logger.exception("Соединение с веб-сокетом разорвано")


async def main():
    # Создаем экземпляр API и запускаем его
    trading_api = TokenTradingAPI(trade_queue=trade_queue)
    await trading_api.start()
    # Получаем WebSocket соединение (создается только один раз)
    websocket = await ws_client.connect()



    await handle_messages(websocket=websocket)
    # Закрываем WebSocket соединение при завершении работы
    await ws_client.close()

    """try:
        await handle_messages(websocket=websocket)
        # Закрываем WebSocket соединение при завершении работы
        await ws_client.close()
    except:
        logger.critical("Завершение программы... ")"""

    # Даем время на выполнение задач
    await trade_queue.join()


# Запуск главной функции
if __name__ == "__main__":
    asyncio.run(main())
