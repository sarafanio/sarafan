"""Application service-bus events.
"""
from dataclasses import dataclass, field

from dataclasses_json import dataclass_json

from .ethereum.contract import BaseContractEvent


def event_field(name, abi_type, indexed=False, hex_bytes=False, ascii_bytes=False):
    """Define field of the ethereum contract.

    You can't set `hex_bytes` and `ascii_bytes` at the same time.

    TODO: move to contract module
    TODO: class-based Field approach might look better

    :param name: field name in the abi
    :param abi_type: abi type
    :param indexed: indexed field or not
    :param hex_bytes: if True, bytes will be decoded to hex with 0x prefix
    :param ascii_bytes: if True, bytes will be decoded to ascii
    :return: field with abi metadata
    """
    return field(metadata={
        "abi_name": name,
        "abi_type": abi_type,
        "abi_indexed": indexed,
        "abi_hex_bytes": hex_bytes,
        "abi_ascii_bytes": ascii_bytes,
    })


@dataclass_json
@dataclass
class Publication(BaseContractEvent):
    """Publication event of content contract.
    """
    reply_to: str = event_field('replyTo', 'bytes32', indexed=True, hex_bytes=True)
    magnet: str = event_field('magnet', 'bytes32', indexed=True, hex_bytes=True)
    source: str = event_field('source', 'address')
    size: int = event_field('magnet', 'uint256')
    retention: int = event_field('magnet', 'uint32')


@dataclass_json
@dataclass
class NewPeer(BaseContractEvent):
    """NewPeer event from the peering contract.
    """
    addr: str = event_field('addr', 'address')
    hostname: str = event_field('hostname', 'bytes32', ascii_bytes=True)
