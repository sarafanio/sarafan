"""Module containing all available service-bus events.

Any service can subscribe or emit them.
"""
from dataclasses import dataclass

from dataclasses_json import dataclass_json

from .ethereum.contract import BaseContractEvent
from .ethereum.event import event_field


@dataclass_json
@dataclass
class Publication(BaseContractEvent):
    """Publication event of Sarafan content contract.

    Emitted by the :py:class:`ContractEventService`.

    Publication should be stored in the database and scheduled to download according
    to download policy. It should be transformed to Post or Comment then.
    """
    #: replyTo magnet hash
    reply_to: str = event_field('replyTo', 'bytes32', indexed=True, hex_bytes=True)
    #: publication magnet hash
    magnet: str = event_field('magnet', 'bytes32', indexed=True, hex_bytes=True)
    #: publication source
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
