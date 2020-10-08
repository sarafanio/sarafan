import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Coroutine, List, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientResponseError, StreamReader
from aiohttp.client import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector, ProxyError, ProxyTimeoutError

from ..magnet import magnet_path
from ..models import Peer

log = logging.getLogger(__name__)


class UnsupportedPeerMethod(Exception):
    pass


class InvalidPeerResponse(Exception):
    pass


# class ConnectionError(Exception):
#     pass


class MagnetError(Exception):
    def __init__(self, magnet, *args):
        self.magnet = magnet
        super().__init__(*args)


class DiscoveryError(MagnetError):
    pass


class UploadError(MagnetError):
    pass


class DownloadError(MagnetError):
    pass


class InvalidChecksum(DownloadError):
    pass


@dataclass
class DiscoveryResult:
    match: List[Peer] = field(default_factory=list)
    near: List[Peer] = field(default_factory=list)


class HelloResult:
    version: Optional[str] = None
    service_id: Optional[str] = None


class PeerClient:
    """Sarafan peer client.

    Allows to connect and communicate with Sarafan peer over tor network.

    `http_proxy` should be provided.
    """
    peer: Peer

    http_proxy: str

    # TODO: rename http_proxy -> socks_proxy
    def __init__(self, peer: Peer, http_proxy: str = "socks5://127.0.0.1:9050"):
        self.peer = peer
        self.http_proxy = http_proxy
        self._connector = ProxyConnector.from_url(http_proxy)

    @property
    def _session(self) -> ClientSession:
        return ClientSession(
            connector=self._connector,
            raise_for_status=True,
            timeout=ClientTimeout(
                total=60, connect=30, sock_read=10
            )
        )

    async def hello(self):
        """Send hello request to the peer.

        Allows to check if peer alive and load general info like content service id
        and node software version.

        Must be invoked before starting any download.

        :raise InvalidPeerResponse: unpredictable response received
        :raise UnsupportedPeerMethod: hello method is not implemented on peer
        """
        log.debug("Requesting hello from peer %s", self.peer)

        data = await self._get(self._url('hello'))

        # update Peer.content_service_id
        content_service_id = data.get('content_service_id')
        if content_service_id and self.peer.content_service_id != content_service_id:
            log.debug("Update peer content service id %s", self.peer)
            self.peer.content_service_id = content_service_id

        # update Peer.version
        peer_version = data.get('version')
        if peer_version and self.peer.version != peer_version:
            log.debug("Update peer version %s", self.peer)
            self.peer.version = peer_version

        log.debug("Hello response processed")
        return data

    async def discover(self, magnet) -> DiscoveryResult:
        """Make discovery request to the node.

        Node will return two lists of peers (both optional):

        * `match` — peers containing requested content
        * `near` — nearest known peers (according to distance between node id and magnet)

        Peers should be verified and may contain a wrong data.

        :raise InvalidPeerResponse: unpredictable response received
        :raise UnsupportedPeerMethod: hello method is not implemented on peer
        """
        discover_body = {
            "magnet": magnet
        }
        log.debug("Making %s discovery request to %s", magnet, self.peer)
        try:
            data = await self._get(self._url('discover'), params=discover_body)
            if 'match' not in data and 'near' not in data:
                log.debug("Peer discovery response didn't contain keys `match` or `near`")
                raise InvalidPeerResponse()
        except (ProxyError, aiohttp.ClientError, ConnectionError, ProxyTimeoutError) as e:
            raise InvalidPeerResponse() from e
        result = DiscoveryResult(
            match=[Peer(**d) for d in data.get('match')],
            near=[Peer(**d) for d in data.get('near')]
        )
        log.debug("Discovery results from peer %s: %s", self.peer, result)
        return result

    async def upload(self, magnet, local_path):
        """Upload magnet content to the node.

        :param magnet:
        :param local_path:
        """
        with open(local_path, 'rb') as fp:
            await self.upload_fp(magnet, fp)

    async def upload_fp(self, magnet, fp):
        """Upload magnet from file pointer.

        :param magnet:
        :param fp:
        """
        params = {
            'url': self._url(f'upload/{magnet}'),
            'data': fp,
        }
        log.info("Uploading magnet %s to peer %s", magnet, self.peer)
        await self._post(**params)
        log.info("Magnet successfully uploaded")

    async def download(self, magnet, store: Callable[[str, StreamReader], Coroutine]):
        """Download specified magnet content to local storage.

        File will be downloaded in file with suffix first. Match file checksum before
        move to the requested destination.
        """
        try:
            async with self._session.get(self.download_url(magnet)) as resp:
                resp.raise_for_status()
                await store(magnet, resp.content)
        except (aiohttp.ClientError, ProxyError) as e:
            raise DownloadError(magnet) from e

    async def has_magnet(self, magnet: str):
        """Check if node storing provided magnet.
        """
        try:
            await self._head(self._content_url(magnet_path(magnet)))
        except (ClientResponseError, ProxyError, ConnectionError):
            # if e.status == 404:
            #     return False
            return False
        return True

    def download_url(self, magnet):
        return self._content_url(magnet_path(magnet))

    @property
    def closed(self):
        """Check if client session was closed.
        """
        return self._session.closed

    async def close(self):
        """Close client and underlying connections.
        """
        if not self._session.closed:
            await self._session.close()

    def _url(self, uri):
        """Build url for peer.
        """
        val = urljoin(f'http://{self.peer.service_id}.onion', uri)
        log.debug("Main service url: %s", val)
        return val

    def _content_url(self, uri):
        """Build url for peer's content node.
        """
        if self.peer.content_service_id:
            return urljoin(
                f'http://{self.peer.content_service_id}.onion',
                uri
            )
        log.debug("Content url: %s", self._url(uri))
        return self._url(uri)

    async def _get(self, *args, **kwargs):
        return await self._request('get', *args, **kwargs)

    async def _post(self, *args, **kwargs):
        return await self._request('post', *args, **kwargs)

    async def _head(self, *args, **kwargs):
        return await self._request('head', *args, **kwargs)

    async def _request(self, method, *args, **kwargs):
        try:
            async with getattr(self._session, method)(*args, **kwargs) as response:
                await self._handle_errors(response)
                return await response.json()
        except (aiohttp.ClientConnectionError, ProxyError, asyncio.TimeoutError, ProxyTimeoutError) as e:
            raise ConnectionError from e

    async def _handle_errors(self, response):
        """Handle standard http errors for each request.

        TODO: handle rate limits and tmp errors
        """
        if response.status // 100 == 2:
            return
        elif response.status == 404:
            log.debug("Peer didn't support such a method. Requested url: %s",
                      response.request_info.url)
            raise UnsupportedPeerMethod()
        else:
            body = await response.content.read(1024 * 50)
            log.debug("Receiving invalid peer %s response for `hello` (status: %i): %s",
                      self.peer, response.status, body)
            raise InvalidPeerResponse()
