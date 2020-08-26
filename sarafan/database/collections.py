import logging
import sqlite3
from typing import TypeVar, Generic

from ..models import Publication, Post

from .mappers import AbstractMapper, DataclassMapper, PostMapper, PublicationMapper


log = logging.getLogger(__name__)

T = TypeVar('T')


class Collection(Generic[T]):
    mapper: AbstractMapper

    def __init__(self, db: str):
        self._db_path = db
        if not hasattr(self, 'mapper'):
            self.mapper = DataclassMapper()

    @property
    def db(self):
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        return db

    @property
    def table_name(self):
        return self.mapper.get_table_name()

    async def get(self, pk):
        """Get object from the collection by primary key.
        """
        with self.db as db:
            pk_column = self.mapper.get_pk_column()
            query = f"SELECT * FROM {self.table_name} WHERE {pk_column}=?"
            cursor = db.cursor()
            log.debug("Retrieve %s with query `%s` %s=%s", self.mapper.model, query, pk_column, pk)
            cursor.execute(query, [pk])
            data = cursor.fetchone()
            # import ipdb; ipdb.set_trace()
            return self.mapper.build_object(data)

    async def store(self, obj: T):
        """Store object in database.
        """
        with self.db as db:
            values = self.mapper.get_insert_data(obj)
            fields = ', '.join(values.keys())
            subs = ','.join(['?'] * len(values))
            query = f"INSERT INTO {self.table_name} ({fields}) VALUES ({subs})"
            cursor = db.cursor()
            log.debug("Store %s with insert query `%s` and args %s", obj, query, values.values())
            cursor.execute(query, list(values.values()))
            db.commit()


class PublicationsCollection(Collection[Publication]):
    mapper = PublicationMapper()


class PostsCollection(Collection[Post]):
    mapper = PostMapper()
