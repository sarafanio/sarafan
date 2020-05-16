import logging.config


def setup_logging(level='INFO'):
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "default": {
                "class": "logging.Formatter",
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
        },
        "root": {
            "level": "INFO",
            "formatter": "default",
            "handlers": ["console"]
        }
    })
