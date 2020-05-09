"""Hash distance helpers.

Helps to calculate distance between two integers. Also provides helpers to convert
ascii strings and hex strings to integer.

Used to calculate distance between peers and magnets.
"""
import math
from functools import lru_cache

from Cryptodome.Hash import keccak


def hex_to_position(value: str):
    """Convert hex string to int position.
    """
    return int(value, 16)


@lru_cache(50)
def ascii_to_position(value: str):
    """Convert ascii string to int position.

    keccak256 hash will be used to normalize strings.
    """
    data = bytes(value, 'ascii')
    return hex_to_position(keccak.new(data=data, digest_bytes=32).hexdigest())


def peer_hash(peer):
    return ascii_to_position(peer.service_id)


def distance(x: int, y: int):
    """Calculate distance between two points.
    """
    return abs(math.sin(x ^ y))


def hash_distance(hash1: str, hash2: str):
    """Distance between two hex-encoded hashes (result of `hexdigest()`).

    Hash lengths should be equal.
    """
    assert len(hash1) == len(hash2), "Hash length should be equal"
    return distance(hex_to_position(hash1), hex_to_position(hash2))


def ascii_distance(s1: str, s2: str):
    """Distance between two ascii strings.

    keccak256 hash will be used to normalize them.
    """
    return distance(ascii_to_position(s1), ascii_to_position(s2))


def ascii_to_hash_distance(s: str, h: str):
    return distance(ascii_to_position(s), hex_to_position(h))
