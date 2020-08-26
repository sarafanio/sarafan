import asyncio
import os
import sys
from asyncio import StreamReader
from typing import Dict, List

import configargparse

from core_service import Service, requirements, task
from eth_account import Account

from sarafan.bundle.bundle import ContentBundle
from sarafan.contract import ContractService
from sarafan.database.service import DatabaseService
from sarafan.download import DownloadService, Download, DownloadStatus
from sarafan.logging_helpers import setup_logging
from sarafan.magnet import is_magnet
from sarafan.models import Post, Publication
from sarafan.onion.controller import HiddenServiceController
from sarafan.peering import Peer
from sarafan.peering.service import PeeringService
from sarafan.onion.service import OnionService
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
argparser.add_argument("--content-path", action="store", dest="content_path",
                       help="Path to the node content directory",
                       default="./content/")
argparser.add_argument("--web-port", action="store", dest="web_port",
                       help="Port for local webserver",
                       default="9231")
argparser.add_argument("--tor-host", action="store", dest="tor_host",
                       help="Host of the tor proxy with exposed control port",
                       default="127.0.0.1")
argparser.add_argument("--tor-socks-port", action="store", dest="tor_socks_port",
                       help="Tor socks proxy port", default="9050")
argparser.add_argument("--tor-control-port", action="store", dest="tor_control_port",
                       help="Tor control port", default="9051")


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

        self.conf.content_path = os.path.abspath(self.conf.content_path)
        os.makedirs(self.conf.content_path, exist_ok=True)

        self.log.info("Content path: %s", self.conf.content_path)

        self.publications_queue = asyncio.Queue()
        self.new_peers_queue = asyncio.Queue()

        self.db = DatabaseService(database=self.conf.db)
        self.contract = ContractService(
            token_address=self.conf.token
        )
        self.peering = PeeringService()
        self.storage = StorageService(base_path=self.conf.content_path)
        self.downloads = DownloadService(
            discovery=self.peering.discover,
            storage=self.storage
        )
        self.web = WebService(
            WebAppInterface(self),
            port=int(self.conf.web_port),
            node_api=self.conf.discover,
            content_api=self.conf.serve,
            client_api=self.conf.client_app,
            content_path=self.conf.content_path,
        )
        # TODO: store and restore keys in order to preserve servece_id between restarts
        self.hidden_service = HiddenServiceController(
            app_port=self.conf.web_port,
            stem_host=self.conf.tor_host,
            stem_port=int(self.conf.tor_control_port),
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
            self.hidden_service,
        ]

    @task()
    async def process_new_publications(self):
        """Process new publications from blockchain.
        """
        publication = await self.publications_queue.get()
        self.log.warning("Received magnet value: %s", publication.magnet)
        publication.magnet = publication.magnet.hex()
        self.log.warning("Decode magnet to %s", publication.magnet)
        self.log.debug("New publication received from contract %s", publication)
        try:
            await self.db.publications.store(publication)
            # TODO: check if it already downloaded
            # TODO: check if it is downloaded but not parsed yet, submit to parse
            await self.downloads.add(publication.magnet)
        except asyncio.CancelledError:
            pass
        except Exception:
            self.log.exception("Exception happens while processing new publication. Skipping.")
        finally:
            self.publications_queue.task_done()

    @task()
    async def process_finished_downloads(self):
        download = await self.downloads.finished.get()
        self.log.info("Process finished %s", download)
        # TODO: update peers stats from download info
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
            self.log.debug("Post stored in the database %s", post)

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
        """Store content uploaded by other peer.

        :param magnet: content magnet
        :param stream: content bundle async stream
        """
        if not is_magnet(magnet):
            raise TypeError("Invalid magnet identifier %s" % magnet)
        await self.app.storage.store(magnet, stream)

    async def publish(self, filename, magnet, private_key):
        """Publish draft post by magnet.

        - content contract `post()`
        - push to known nodes
        """
        account = Account.from_key(private_key)
        # log.info("Post to contract from %s", account.address)
        await self.app.contract.post_service.post(
            address=account.address,
            private_key=private_key,
            reply_to=b'0',
            magnet=bytes.fromhex(magnet),
            size=os.path.getsize(filename),
            author=account.address
        )
        # log.info("Schedule distribution...")
        # make a look like a file was downloaded
        await self.app.db.publications.store(Publication(
            magnet=magnet,
            reply_to='0x',
            retention=12,
            source='0x',
            size=os.path.getsize(filename)
        ))
        target_filename = self.app.storage.get_absolute_path(magnet)
        self.app.log.warning("Target filename: %s", target_filename)
        target_filename.parent.mkdir(parents=True)
        os.rename(filename, target_filename)
        self.app.log.warning("Put download as finished to queue %s", magnet)
        await self.app.downloads.finished.put(
            Download(
                magnet=magnet,
                status=DownloadStatus.FINISHED,
                log=[]
            )
        )

        # distribute file over network
        await self.app.peering.distribute(target_filename, magnet)
