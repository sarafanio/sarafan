import logging
import sqlite3
from base64 import b64decode, b64encode
from typing import TypeVar, Generic
from urllib.parse import parse_qs, urlencode

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

    def all(self, cursor=None, per_page=2):
        args = []
        query = f"SELECT ROWID, * FROM {self.table_name} "
        if cursor is not None:
            cursor_data = parse_qs(b64decode(cursor.encode()))
            parse_qs(b64decode(cursor.encode()), encoding='utf-8')
            # import ipdb; ipdb.set_trace()
            last_time = cursor_data[b't'][0].decode()
            last_rowid = cursor_data[b'r'][0].decode()
            query += f"WHERE created_at <= ? AND ROWID < ? "
            args += [last_time, last_rowid]
        query += f"ORDER BY created_at DESC LIMIT {per_page}"
        with self.db as db:
            cursor = db.cursor()
            cursor.execute(query, args)
            result = cursor.fetchall()
        next_cursor = None
        if len(result) == per_page:
            next_cursor = b64encode(urlencode({
                't': result[-1]['created_at'],
                'r': result[-1]['ROWID']
            }).encode()).decode()
        return [self.mapper.build_object(item) for item in result], next_cursor
