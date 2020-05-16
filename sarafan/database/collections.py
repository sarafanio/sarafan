import sqlite3
from typing import TypeVar, Generic

from sarafan.database.mappers import AbstractMapper, DataclassMapper

T = TypeVar('T')


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
