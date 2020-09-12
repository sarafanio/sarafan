from dataclasses import fields
from typing import TypeVar, Generic, Type, Dict

from sarafan.events import Publication, Post

T = TypeVar('T')


class AbstractMapper(Generic[T]):
    model: Type[T]
    table_name: str

    def __init__(self, model: Type[T] = None, table_name: str = None):
        if model is not None:
            self.model = model
        if not hasattr(self, 'model') or self.model is None:
            raise RuntimeError(f"Model should be defined on derived class or provided"
                               f"as an argument to the {self.__class__} constructor.")
        if table_name is not None:
            self.table_name = table_name
        if not hasattr(self, 'table_name') or self.table_name is None:
            raise RuntimeError(f"Table name should be defined on derived class or provided"
                               f"as an argument to the {self.__class__} constructor")

    def get_table_name(self) -> str:
        return self.table_name

    def get_pk_column(self) -> str:
        return 'id'

    def build_object(self, data) -> T:
        pass

    def get_insert_data(self, obj: T) -> Dict:
        pass


class DataclassMapper(AbstractMapper[T]):
    def build_object(self, data) -> T:
        props = {}
        for field in fields(self.model):
            col_name = field.name
            if field.metadata and 'db_name' in field.metadata:
                col_name = field.metadata['db_name']
            props[field.name] = data[col_name]
        return self.model(**props)

    def get_insert_data(self, obj: T) -> Dict:
        values = {}
        for field in fields(self.model):
            col_name = field.name
            if field.metadata and 'db_name' in field.metadata:
                col_name = field.metadata['db_name']
            v = getattr(obj, field.name)
            if v is not None:
                values[col_name] = v
        return values


class PostMapper(DataclassMapper[Post]):
    model = Post
    table_name = 'sarafan_posts'

    def get_pk_column(self):
        return 'magnet'


class PublicationMapper(DataclassMapper[Publication]):
    model = Publication
    table_name = 'sarafan_publications'

    def get_pk_column(self):
        return 'magnet'
