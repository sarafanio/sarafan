import inspect
import sqlite3
from typing import TypeVar, Generic
from pathlib import Path

from core_service import Service

from .migrations import apply_migrations


T = TypeVar('T')


class AbstractMapper:
    def get_table_name(self) -> str:
        return 'tmp_table_name'

    def get_pk_column(self) -> str:
        return 'id'


class DataclassMapper(AbstractMapper):
    pass


class Collection(Generic[T]):
    mapper: AbstractMapper

    def __init__(self, db: sqlite3.Connection):
        self._db = db
        if not hasattr(self, 'mapper'):
            self.mapper = DataclassMapper()

    async def get(self, pk):
        """Get object from the collection by primary key.
        """
        table_name = self.mapper.get_table_name()
        pk_column = self.mapper.get_pk_column()
        query = f"SELECT * FROM {table_name} WHERE {pk_column}=?"
        cursor = self._db.cursor()
        cursor.execute(query, pk)
        data = cursor.fetchone()

    async def store(self, obj: T):
        """Store object in database.
        """
        pass


class PublicationsCollection(Collection):
    pass


class PostsCollection(Collection):
    pass


class CommentsCollection(Collection):
    pass


class DatabaseService(Service):
    publications = PublicationsCollection
    posts = PostsCollection
    comments = CommentsCollection

    def __init__(self, database: str = ':memory:', **kwargs):
        super().__init__(**kwargs)
        if database != ':memory:':
            database = str(Path(database).resolve())
        self.log.info("Starting with database %s", database)
        self._db_path = database
        self._db = sqlite3.connect(database)
        self._initialize_collections()

    def _initialize_collections(self):
        for name, value in inspect.getmembers(self, lambda x: isinstance(x, type) and issubclass(x, Collection)):
            setattr(self, name, value(db=self._db))

    async def start(self):
        self.log.info("Applying migrations...")
        apply_migrations(self._db_path)
        self.log.info("Migrations applied")
        await super().start()

    async def stop(self):
        await super().stop()
        self._db.commit()
        self._db.close()
        self.log.info("Database connection was closed")
