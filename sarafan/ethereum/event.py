from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Event:
    log_index: int
    block_number: int
    block_hash: str
    transaction_hash: str
    transaction_index: int
    address: str
    data: str
    topics: List[str]

    @classmethod
    def from_raw_event(cls, raw: Dict) -> "Event":
        """Create Event instance from node' eth_getLogs response.

        :param raw: dict with raw event data
        """
        return Event(
            log_index=int(raw["logIndex"], 16),
            block_number=int(raw["blockNumber"], 16),
            block_hash=raw["blockHash"],
            transaction_hash=raw["transactionHash"],
            transaction_index=int(raw["transactionIndex"], 16),
            address=raw["address"],
            data=raw["data"],
            topics=raw["topics"],
        )


def event_field(name, abi_type, indexed=False, hex_bytes=False, ascii_bytes=False):
    """Define field of the ethereum contract on the dataclass.

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
