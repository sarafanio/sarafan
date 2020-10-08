import asyncio

from core_service import Service, listener

from .events import DiscoveryFinished, DownloadRequest, DiscoveryRequest, Publication, DownloadFinished
from .peering.client import InvalidChecksum, DownloadError, PeerClient
from .storage import StorageService


class DownloadService(Service):
    """Download service.

    Handle download queue. New download can be added with `add` method. Content hash (magnet) should
    be provided. Then, `download_task` will handle discovery and actually download content file.

    Clients should listen to `finished` queue for download status.
    """
    #: storage service instance
    storage: StorageService

    #: internal queue with Download items to download
    download_queue: asyncio.Queue

    def __init__(self,
                 storage: StorageService,
                 **kwargs):
        super().__init__(**kwargs)
        self.storage = storage

        self.download_queue = asyncio.Queue()
        self.finished = asyncio.Queue()
        self.failed = asyncio.Queue()

    def should_download_magnet(self, magnet):
        """Should current node download provided magnet or not.

        Make decision based on the distance etc.

        TODO: implementation
        """
        return True

    @listener(Publication)
    async def process_new_publications(self, publication: Publication):
        """Process new publications from blockchain.
        """
        # TODO: check if it already downloaded
        # TODO: check if it is downloaded but not parsed yet, submit to parse
        if self.should_download_magnet(publication.magnet):
            # it might be more viable to emit DownloadRequest first
            await self.emit(DiscoveryRequest(publication=publication))
        else:
            self.log.debug("Won't download publication %s because of download service policy",
                           publication)

    @listener(DownloadRequest)
    async def process_download_request(self, request: DownloadRequest):
        """Process download request.

        Instead of new publications it is a forced way to download content
        without distance check etc.
        """
        await self.emit(DiscoveryRequest(publication=request.publication))

    @listener(DiscoveryFinished)
    async def finished_discovery_handler(self, event: DiscoveryFinished):
        """DiscoveryFinished event handler.

        Start download content bundle from discovered peer.

        Emit DownloadFinished event on success which can be handled to
        unpack and store publication in db and/or to add new file to the merkle
        hash tree.
        """
        magnet = event.publication.magnet
        client = PeerClient(event.peer)

        try:
            await client.download(magnet, self.storage.store)
            await self.emit(DownloadFinished(publication=event.publication))
            return
        except InvalidChecksum:
            # TODO: need to decrease peer rating
            self.log.warning("Invalid content checksum for magnet %s from peer %s",
                             magnet, client.peer)
        except DownloadError:
            self.log.error("Error while downloading magnet %s from peer %s",
                           magnet, client.peer, exc_info=True)
        # TODO: it might be better to emit DownloadFailed and dispatch it in the Scheduler
        # emit new discovery request in case of failure
        await self.emit(DiscoveryRequest(publication=event.publication, state=event.state))
