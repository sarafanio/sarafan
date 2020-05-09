import inspect
from typing import TypeVar, Generic

from core_service import Service


T = TypeVar('T')


class Collection(Generic[T]):
    def store(self, obj):
        pass


class PublicationsCollection(Collection):
    pass


class DatabaseService(Service):
    publications = PublicationsCollection

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initialize_collections()

    async def store_publication(self, obj):
        pass

    async def store_post(self, obj):
        pass

    async def store_award(self, obj):
        pass

    async def store_comment(self, obj):
        pass

    def _initialize_collections(self):
        for name, value in inspect.getmembers(self, lambda x: isinstance(x, Collection)):
            collection = value()
            setattr(self, name, collection)
