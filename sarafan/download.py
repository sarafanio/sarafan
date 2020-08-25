import asyncio
import enum
from dataclasses import dataclass, field
import time
from typing import Callable, AsyncGenerator, Optional, List

from core_service import Service, task

from .peering import PeerClient, Peer
from .peering.client import InvalidChecksum, DownloadError
from .peering.service import MagnetNotDiscovered
from .storage import StorageService


class DownloadStatus(enum.Enum):
    #: new or queued download
    PENDING = 'PENDING'
    #: magnet discovery started
    DISCOVERY = 'DISCOVERY'
    #: download in progress
    DOWNLOAD = 'DOWNLOAD'
    #: download finished successfully
    FINISHED = 'FINISHED'
    #: download failed
    FAILED = 'FAILED'


@dataclass
class PeerResult:
    #: download time
    timestamp: float
    #: download from peer
    peer: Peer
    #: is peer alive at the moment of download
    peer_alive: bool = False
    #: is magnet content found on peer
    magnet_found: bool = False
    #: is magnet content downloaded successfully
    success: bool = False
    #: download time in seconds
    download_time: Optional[float] = None
    #: downloaded size
    download_size: Optional[int] = None
    #: optional message (error reason)
    message: str = ""


@dataclass
class Download:
    magnet: str
    status: DownloadStatus = DownloadStatus.PENDING
    log: List[PeerResult] = field(default_factory=list)


class DownloadService(Service):
    """Download manager service.

    Handle download queue. New download can be added with `add` method. Content hash (magnet) should
    be provided. Then, `download_task` will handle discovery and actually download content file.

    Clients should listen to `finished` queue for download status.
    """
    #: discovery function
    discovery: Callable[[str], AsyncGenerator[PeerClient, None]]
    #: storage service instance
    storage: StorageService

    #: internal queue with Download items to download
    download_queue: asyncio.Queue
    #: queue with finished Download items
    finished: asyncio.Queue
    #: queue with failed Download items
    failed: asyncio.Queue

    def __init__(self,
                 discovery: Callable[[str], AsyncGenerator[PeerClient, None]],
                 storage: StorageService,
                 **kwargs):
        super().__init__(**kwargs)
        self.discovery = discovery
        self.storage = storage

        self.download_queue = asyncio.Queue()
        self.finished = asyncio.Queue()
        self.failed = asyncio.Queue()

    async def add(self, magnet: str):
        """Add magnet to download queue.
        """
        obj = Download(magnet)
        await self.download_queue.put(obj)

    async def download(self, download: Download):
        """Actually download magnet.
        """
        magnet = download.magnet
        download.status = DownloadStatus.DISCOVERY
        try:
            async for client in self.discovery(magnet):
                peer_result = PeerResult(
                    timestamp=time.monotonic_ns(),
                    peer=client.peer
                )
                try:
                    download.status = DownloadStatus.DOWNLOAD
                    await client.download(magnet, self.storage.store)
                    download.status = DownloadStatus.FINISHED
                    peer_result.peer_alive = True
                    peer_result.magnet_found = True
                    peer_result.success = True
                    peer_result.download_time = time.monotonic_ns() - peer_result.timestamp
                except InvalidChecksum:
                    # TODO: need to decrease peer rating
                    download.status = DownloadStatus.DISCOVERY
                    peer_result.peer_alive = True
                    peer_result.magnet_found = True
                    peer_result.message = "Invalid checksum"
                    self.log.warning("Invalid content checksum for magnet %s from peer %s",
                                     magnet, client.peer)
                except DownloadError:
                    peer_result.message = "HTTP error"
                    self.log.error("Error while downloading magnet %s from peer %s",
                                   magnet, client.peer, exc_info=True)
                download.log.append(peer_result)
                if download.status == DownloadStatus.FINISHED:
                    return download
        except MagnetNotDiscovered:
            self.log.info("Magnet is not discovered and will be scheduled to download later")
            # FIXME: schedule "to download later"
            self.log.warning("Delayed download doesn't implemented yet")

    @task()
    async def download_task(self):
        download = await self.download_queue.get()
        await self.download(download)
