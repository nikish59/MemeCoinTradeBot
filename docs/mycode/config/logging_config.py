import logging
from logging.handlers import RotatingFileHandler
import os

# Директория для лог-файлов
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str, log_file: str, level=logging.INFO, console_output=True, global_log_file=True):
    """
    Настраивает логгер с именем `name`, записывающий логи в `log_file`.
    Параметры:
    - console_output: если True, выводить логи в консоль.
    - global_log_file: если True, добавлять запись в общий лог для всех.
    """
    log_file_path = os.path.join(LOG_DIR, log_file)

    # Создаем обработчик для ротации лог-файлов
    handler = RotatingFileHandler(log_file_path, maxBytes=10**8, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Создаем и настраиваем логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Если console_output=True, добавляем обработчик для вывода в консоль
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Если global_log_file=True, добавляем запись в общий лог
    if global_log_file:
        global_log_path = os.path.join(LOG_DIR, "global.log")  # Общий лог-файл для всех
        global_handler = RotatingFileHandler(global_log_path, maxBytes=10**8, backupCount=3)
        global_handler.setLevel(logging.DEBUG)
        global_handler.setFormatter(formatter)
        logger.addHandler(global_handler)

    return logger
