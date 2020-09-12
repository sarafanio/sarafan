import factory

from sarafan.events import Publication

from .utils import generate_rnd_hash, generate_rnd_address


class PublicationFactory(factory.Factory):
    class Meta:
        model = Publication
    reply_to = '0x'
    magnet = factory.LazyFunction(lambda: generate_rnd_hash()[2:])
    source = factory.LazyFunction(generate_rnd_address)
    size = 1
    retention = 1
