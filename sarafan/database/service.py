import inspect
import sqlite3
from pathlib import Path

from core_service import Service

from .collections import (
    Collection,
    PostsCollection,
    PublicationsCollection,
)
from .migrations import apply_migrations


class DatabaseService(Service):

    """Database service.

    Manage set of collections with a business-oriented interface.
    """

    publications = PublicationsCollection
    posts = PostsCollection
    # comments = CommentsCollection

    def __init__(self, database: str = ':memory:', **kwargs):
        super().__init__(**kwargs)
        if database != ':memory:':
            database = str(Path(database).resolve())
        self.log.info("Starting with database %s", database)
        self._db_path = database
        self._db = sqlite3.connect(database)
        self._db.row_factory = sqlite3.Row
        self._initialize_collections()

    def _initialize_collections(self):
        for name, value in inspect.getmembers(self, lambda x: isinstance(x, type) and issubclass(x, Collection)):
            setattr(self, name, value(db=self._db))

    async def start(self):
        apply_migrations(self._db_path)
        await super().start()

    async def stop(self):
        await super().stop()
        self._db.commit()
        self._db.close()
        self.log.info("Database connection was closed")
