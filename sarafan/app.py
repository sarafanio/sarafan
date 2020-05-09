import asyncio
import sys

import configargparse

from core_service import Service, requirements, task

from sarafan.contract import ContractService
from sarafan.database.service import DatabaseService
from sarafan.download import DownloadService
from sarafan.peering.service import PeeringService
from sarafan.storage import StorageService

argparser = configargparse.get_argument_parser()
argparser.add_argument("--token", help="Sarafan token contract address",
                       default="0x957D0b2E4afA74A49bbEa4d7333D13c0b11af60F")


class Application(Service):
    #: application config
    conf: configargparse.Namespace

    contract: ContractService

    #: main queue with new publications from blockchain
    publications_queue: asyncio.Queue
    #: queue with downloaded publications to parse and store
    downloaded_publications_queue: asyncio.Queue

    def __init__(self, argv=None, **kwargs):
        super().__init__(**kwargs)
        self.argv = argv or sys.argv
        self.conf = argparser.parse_known_args(self.argv)[0]

        self.publications_queue = asyncio.Queue()

        self.db = DatabaseService()
        self.contract = ContractService(
            token_address=self.conf.token
        )
        self.peering = PeeringService()
        self.storage = StorageService(base_path='./content')
        self.downloads = DownloadService(
            discovery=self.peering.discover,
            storage=self.storage
        )

    @requirements()
    async def app_req(self):
        # resolve contract service before accessing contracts
        await self.contract.resolve()
        content_contract = self.contract.content.contract

        # subscribe to publications from content contract
        Publication = content_contract.event('Publication')
        self.contract.content.subscribe(Publication, queue=self.publications_queue)

        return [
            self.contract
        ]

    @task()
    async def process_new_publications(self):
        """Process new publications from blockchain.
        """
        publication = await self.publications_queue.get()
        self.log.debug("New publication received from contract %s", publication)
        await self.db.publications.store(publication)
        # TODO: check if it already downloaded
        await self.downloads.add(publication.magnet)
        # TODO: check if it is downloaded but not parsed yet, submit to parse

    @task()
    async def process_finished_downloads(self):
        download = await self.downloads.finished.get()
        # parse content
        # store in db as comment or post
