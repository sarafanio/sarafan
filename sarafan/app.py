import asyncio
import sys
from asyncio import StreamReader
from typing import Dict, List

import configargparse

from core_service import Service, requirements, task
from sarafan.bundle.bundle import ContentBundle
from sarafan.contract import ContractService
from sarafan.database.service import DatabaseService
from sarafan.download import DownloadService
from sarafan.logging import setup_logging
from sarafan.magnet import is_magnet
from sarafan.models import Post
from sarafan.peering import Peer
from sarafan.peering.service import PeeringService
from sarafan.storage import StorageService
from sarafan.web import WebService
from sarafan.web.service import AbstractApplicationInterface

argparser = configargparse.get_argument_parser()
argparser.add_argument("--token", help="Sarafan token contract address",
                       default="0x957D0b2E4afA74A49bbEa4d7333D13c0b11af60F")
argparser.add_argument("--db", help="sqlite database path",
                       default="db.sqlite")
argparser.add_argument("--log-level", help="log level to output",
                       default="INFO", choices=('DEBUG', 'INFO', 'ERROR'))
argparser.add_argument("--no-discover", action="store_false", dest="discover",
                       help="Disable p2p network discover")
argparser.add_argument("--no-serve", action="store_false", dest="serve",
                       help="Don't expose stored content to network")
argparser.add_argument("--no-app", action="store_false", dest="client_app",
                       help="Disable client app endpoints")


class Application(Service):
    """Sarafan application.

    Handle configuration and components coupling.
    """
    #: application config
    conf: configargparse.Namespace

    contract: ContractService

    #: queue with new publications from blockchain
    publications_queue: asyncio.Queue
    #: queue with NewPeer events from contract
    new_peers_queue: asyncio.Queue

    def __init__(self, argv=None, **kwargs):
        super().__init__(**kwargs)
        self.argv = argv or sys.argv
        self.conf = argparser.parse_known_args(self.argv)[0]

        setup_logging(self.conf.log_level)

        self.publications_queue = asyncio.Queue()
        self.new_peers_queue = asyncio.Queue()

        self.db = DatabaseService(database=self.conf.db)
        self.contract = ContractService(
            token_address=self.conf.token
        )
        self.peering = PeeringService()
        self.storage = StorageService(base_path='./content')
        self.downloads = DownloadService(
            discovery=self.peering.discover,
            storage=self.storage
        )
        self.web = WebService(
            WebAppInterface(self),
            node_api=self.conf.discover,
            content_api=self.conf.serve,
            client_api=self.conf.client_app,
        )

    @requirements()
    async def app_req(self):
        # resolve contract service before accessing contracts
        await self.contract.resolve()
        content_contract = self.contract.content.contract

        # subscribe to publications from content contract
        Publication = content_contract.event('Publication')
        self.contract.content.subscribe(Publication, queue=self.publications_queue)

        # Subscribe to new peers from peering contract
        NewPeer = self.contract.peering.contract.event('NewPeer')
        self.contract.peering.subscribe(NewPeer, queue=self.new_peers_queue)

        return [
            self.contract,
            self.db,
            self.downloads,
            self.peering,
            self.storage,
            self.web,
        ]

    @task()
    async def process_new_publications(self):
        """Process new publications from blockchain.
        """
        publication = await self.publications_queue.get()
        self.log.debug("New publication received from contract %s", publication)
        await self.db.publications.store(publication)
        # TODO: check if it already downloaded
        # TODO: check if it is downloaded but not parsed yet, submit to parse
        await self.downloads.add(publication.magnet)

    @task()
    async def process_finished_downloads(self):
        download = await self.downloads.finished.get()
        # TODO: update peers from download
        bundle_path = self.storage.get_absolute_path(download.magnet)
        with ContentBundle(bundle_path, 'r') as bundle:
            markdown_content = bundle.render_markdown()
            unpack_path = self.storage.get_unpack_path(download.magnet)
            bundle.extractall(unpack_path)
        publication = await self.db.publications.get(download.magnet)
        if publication.reply_to:
            self.log.error("Comments not implemented yet, skip")
            return
        else:
            post = Post(magnet=download.magnet, content=markdown_content)
            self.db.posts.store(post)

    @task()
    async def process_new_peers(self):
        new_peer_event = await self.new_peers_queue.get()
        self.log.info("New peer received from contract %s", new_peer_event)
        peer = Peer(service_id=new_peer_event.hostname)
        await self.peering.add_peer(peer)


class WebAppInterface(AbstractApplicationInterface):
    """WebApp interface.

    Implementation of webapps abstract application interface.
    """
    def __init__(self, app: Application):
        self.app = app

    async def hello(self) -> Dict:
        """Hello response content.
        """
        return {
            'service_id': 'test'
        }

    async def hot_peers(self) -> List[Peer]:
        """In-memory peers list.
        """
        return self.app.peering.peers_by_rating[:100]

    async def store_upload(self, magnet: str, stream: StreamReader):
        if not is_magnet(magnet):
            raise TypeError("Invalid magnet identifier %s" % magnet)
        await self.app.storage.store(magnet, stream)
