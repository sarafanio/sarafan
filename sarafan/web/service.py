from abc import ABC, abstractmethod
from asyncio import StreamReader
from typing import Dict, List

from aiohttp import web

from core_service import Service

from ..peering import Peer
from .handlers import setup_routes


class AbstractApplicationInterface(ABC):

    """Abstract application interface.

    This interface implemented on the sarafan app side and
    expose some sarafan app services functionality for handlers.
    It helps to abstract handlers from sarafan app implementation details.
    """

    @abstractmethod
    async def hello(self) -> Dict:
        """Hello response data.

        This method should return complete hello response json according
        to the specification.

        Instead of `ping` it is designed to be static and can be heavily cached.

        Example response:

            {
                "version": "1.0",
                "content_service_id": 'hiddenservice',
            }
        """
        pass

    @abstractmethod
    async def hot_peers(self) -> List[Peer]:
        """Get list of the best peers.

        Used by webapp to respond to `discovery` without specified magnet.
        """
        pass

    async def nearest_peers(self, magnet) -> List[Peer]:
        """Get list of peers with closest distance to the magnet.

        Used by webapp to respond to `discovery` with specified magnet.

        Default implementation return the same peer list as `hot_peers`.

        :param magnet: magnet to measure distance
        """
        return await self.hot_peers()

    async def store_upload(self, magnet: str, stream: StreamReader):
        """Store upload received from other node or client over http.

        :param magnet:
        :param stream:
        :return:
        """
        pass


class WebService(Service):

    """Sarafan web service.

    Setup and run http server exposing node, content and/or client api.
    """

    host: str
    port: int
    runner: web.AppRunner

    def __init__(self,
                 app: AbstractApplicationInterface,
                 node_api: bool = True,
                 content_api: bool = True,
                 client_api: bool = True,
                 host: str = '0.0.0.0',
                 port: int = 8080,
                 **kwargs):
        self.app = app

        self.node_api_enabled = node_api
        self.content_api_enabled = content_api
        self.client_api_enabled = client_api

        self.host = host
        self.port = port

        super().__init__(**kwargs)

    async def start(self):
        await super().start()

        webapp = web.Application()
        webapp['sarafan'] = self.app

        setup_routes(webapp)

        self.runner = web.AppRunner(webapp)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        self.log.info("WebServer started on %s:%s", self.host, self.port)

    async def stop(self):
        self.log.info("Stopping WebServer")
        await self.runner.cleanup()
        await super().stop()
