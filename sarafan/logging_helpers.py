import logging
from colorama import init as colorama_init, Fore, Style
import logging.config


colorama_init()


def setup_logging(level='INFO'):
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "class": "sarafan.logging_helpers.ColoredLogFormatter",
                "format": "%(asctime)s %(levelname)-7s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "loggers": {
            "sarafan": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            "aiohttp.server": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            "aiohttp.access": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            }
        },
        "root": {
            "level": "INFO",
            "formatter": "default",
            "handlers": ["console"]
        }
    })


class ColoredLogFormatter(logging.Formatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        msg = super().formatMessage(record)
        if record.levelname == 'ERROR':
            return Fore.RED + Style.BRIGHT + msg + Style.RESET_ALL
        elif record.levelname == 'WARNING':
            return Fore.YELLOW + msg + Style.RESET_ALL
        elif record.levelname == 'DEBUG':
            return Style.DIM + msg + Style.RESET_ALL
        return msg
