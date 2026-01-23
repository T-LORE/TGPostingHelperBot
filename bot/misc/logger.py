import os
import logging
from logging.handlers import RotatingFileHandler
import colorlog

def configure_logger():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    console_format = (
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s: %(message)s"
    )
    
    file_format = (
        "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(name)s | %(message)s"
    )

    colors = {
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    }

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(colorlog.ColoredFormatter(
        console_format,
        datefmt="%H:%M:%S",
        log_colors=colors,
        reset=True
    ))

    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        maxBytes=5 * 1024 * 1024, 
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(file_format))

    error_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "errors.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR) 
    error_file_handler.setFormatter(logging.Formatter(file_format))

    logging.basicConfig(
        level=logging.NOTSET,
        handlers=[console_handler, file_handler, error_file_handler]
    )

    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    # logging.getLogger("aiogram.event").setLevel(logging.WARNING)