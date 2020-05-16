import pytest

from .utils import generate_rnd_hash, generate_rnd_address


@pytest.fixture(scope='session')
def rnd_hash():
    return generate_rnd_hash


@pytest.fixture(scope='session')
def rnd_address(rnd_hash):
    return generate_rnd_address
