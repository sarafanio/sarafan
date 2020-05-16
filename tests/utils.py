from random import randint

from Cryptodome.Hash import keccak


def generate_rnd_hash(digest_bytes=32):
    return "0x%s" % keccak.new(
        data=b'%i' % randint(0, 10000),
        digest_bytes=digest_bytes
    ).hexdigest()


def generate_rnd_address():
    return str(generate_rnd_hash(28)[:42])
