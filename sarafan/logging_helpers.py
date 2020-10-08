import logging
from pprint import pformat as original_pformat
from colorama import init as colorama_init, Fore, Style
import logging.config


colorama_init()


class pformat:  # noqa
    """Lazy pformat.

    Useful for debug logging: it will not affect runtime.
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return original_pformat(*self.args, **self.kwargs)


def setup_logging(level='INFO', ethereum_level='INFO'):
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
            "sarafan.ethereum": {
                "level": ethereum_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "sarafan.contract": {
                "level": ethereum_level,
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
            },
            "core_service": {
                "level": "INFO",
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
