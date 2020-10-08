import inspect
from pathlib import Path

from core_service import Service, listener, task

from .collections import (
    Collection,
    PostsCollection,
    PublicationsCollection,
    PeersCollection,
)
from .migrations import apply_migrations
from ..models import Peer


class DatabaseService(Service):

    """Database service.

    Manage set of collections with a business-oriented interface.
    """

    publications: PublicationsCollection = PublicationsCollection
    posts: PostsCollection = PostsCollection
    peers: PeersCollection = PeersCollection
    # comments = CommentsCollection

    def __init__(self, database: str = ':memory:', **kwargs):
        super().__init__(**kwargs)
        if database != ':memory:':
            database = str(Path(database).resolve())
        self.log.info("Starting with database %s", database)
        self._db_path = database
        self._initialize_collections()

    def _initialize_collections(self):
        for name, value in inspect.getmembers(self, lambda x: isinstance(x, type) and issubclass(x, Collection)):
            setattr(self, name, value(db=self._db_path))

    async def start(self):
        apply_migrations(self._db_path)
        await super().start()

    async def stop(self):
        await super().stop()
        self.log.info("Database connection was closed")

    @listener(Peer)
    async def store_peers(self, peer: Peer):
        """Store all Peers emited on service bus in the database.
        """
        await self.peers.store(peer)

    @task(periodic=False)
    async def restore_peers(self):
        self.log.info("Restoring peers from the database")
        for peer in self.peers.all():
            self.log.info("Restoring peer %s", peer)
            await self.emit(peer)
