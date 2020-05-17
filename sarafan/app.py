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


class Application(Service):
    """Sarafan application.

    Handle configuration and components coupling.
    """
    #: application config
    conf: configargparse.Namespace

    contract: ContractService

    #: queue with new publications from blockchain
    publications_queue: asyncio.Queue

    def __init__(self, argv=None, **kwargs):
        super().__init__(**kwargs)
        self.argv = argv or sys.argv
        self.conf = argparser.parse_known_args(self.argv)[0]

        setup_logging(self.conf.log_level)

        self.publications_queue = asyncio.Queue()

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
        # TODO: toggle services to match configuration
        self.web = WebService(WebAppInterface(self))

    @requirements()
    async def app_req(self):
        # resolve contract service before accessing contracts
        await self.contract.resolve()
        content_contract = self.contract.content.contract

        # subscribe to publications from content contract
        Publication = content_contract.event('Publication')
        self.contract.content.subscribe(Publication, queue=self.publications_queue)

        return [
            self.contract,
            self.db,
            self.storage,
            self.peering,
            self.downloads,
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

    def hello(self):
        """Hello node response.

        Used by webapp handlers.
        """
        return {
            "version": "PRE-ALPHA",
            "content_service_id": 'dontknow',
        }


class WebAppInterface(AbstractApplicationInterface):
    def __init__(self, app: Application):
        self.app = app

    async def hello(self) -> Dict:
        return {
            'service_id': 'test'
        }

    async def hot_peers(self) -> List[Peer]:
        return [
            Peer('example'),
            Peer('example2')
        ]

    async def store_upload(self, magnet: str, stream: StreamReader):
        if not is_magnet(magnet):
            raise TypeError("Invalid magnet identifier %s" % magnet)
        await self.app.storage.store(magnet, stream)
