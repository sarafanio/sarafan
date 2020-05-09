from dataclasses import dataclass
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
