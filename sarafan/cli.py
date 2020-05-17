import sys
import logging
from asyncio import get_event_loop

from .app import Application


async def _make_app():
    return Application(sys.argv)


def cli(run_forever=True):
    loop = get_event_loop()
    app = loop.run_until_complete(_make_app())
    try:
        loop.run_until_complete(app.start())
        if run_forever:  # noqa
            loop.run_forever()
    except KeyboardInterrupt:
        sys.stdout.write(' - Ctrl + C pressed\n')
        logging.info("Starting shutdown sequence. "
                     "Press Ctrl + C second time to force shutdown "
                     "(you may lost some data)")
    finally:
        try:
            loop.run_until_complete(app.stop())
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            logging.info("Graceful shutdown complete.")
            exit(0)
        except KeyboardInterrupt:
            logging.error("Shutdown interrupted. Some data may lost.")
            exit(1)
