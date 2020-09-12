"""Module containing all available service-bus events.

Any service can subscribe or emit them. Some of the events stored in the database if emitted.
"""
from dataclasses import dataclass, field
from typing import Set

from dataclasses_json import dataclass_json

from .ethereum.contract import BaseContractEvent
from .ethereum.event import event_field
from .models import Peer


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
    #: bundle size in bytes
    size: int = event_field('magnet', 'uint256')
    #: retention time paid on publication time
    retention: int = event_field('magnet', 'uint32')


@dataclass_json
@dataclass
class DownloadRequest:
    """Download request bus event.

    The main scenario of emitting DownloadRequest is when we received new publication
    from the blockchain and decided to download it.

    The other possible scenario is to emitting it by scheduler service looking for download
    retries.

    Download requests are consumed by the download service at first. It should check if
    publication already downloaded and is valid before trying to actually discover
    the magnet. Download service should emit DiscoveryRequest then to start magnet discovery
    process.
    """
    #: publication requested to download
    publication: Publication


@dataclass_json
@dataclass
class DiscoveryState:
    """Discovery state.

    Isn't an event by itself.

    Returned as part of the DiscoveryFinished event and can be passed as part
    of the DiscoveryRequest to start discovery from the last place and skip already failed
    peers.
    """
    #: number of current retry, 0 for the first try
    retry_number: int = 0
    #: tried peers which will be ignored on the next discovery
    visited_peers: Set[Peer] = field(default_factory=set)


@dataclass_json
@dataclass
class DiscoveryRequest:
    """Discovery request bus event.

    Emitted by DownloadService and consumed by PeeringService.

    Peering service should start discovery process and emit DiscoveryFinished at the end.
    """
    #: publication to discover
    publication: Publication
    #: previous discovery state
    state: DiscoveryState = field(default_factory=DiscoveryState)


@dataclass_json
@dataclass
class DiscoveryFinished:
    """Discovery finished bus event

    Emitted by PeeringService in response to DiscoveryRequest.

    Consumed by DownloadService to actually start download of the content bundle from the peer.
    DownloadService can re-emmit DiscoveryRequest with a list of failed peers if real download
    attempt failed. Post or Comment should be emitted after successful download.
    """
    #: discovered publication location
    publication: Publication
    #: discovered peer
    peer: Peer
    #: direct download url
    url: str
    #: discovery state
    state: DiscoveryState = field(default_factory=DiscoveryState)


@dataclass_json
@dataclass
class DiscoveryFailed:
    """Discovery failed bus event.

    Emitted by peering service in case magnet discovery failed over the whole visible sarafan
    network.

    Consumed by the scheduler service to reschedule discovery after some period of time.
    """
    publication: Publication
    state: DiscoveryState = field(default_factory=DiscoveryState)


@dataclass_json
@dataclass
class NewPeer(BaseContractEvent):
    """NewPeer event from the peering contract.

    Emitted by the ContractEventService and consumed by the PeeringService to discover
    new peers.
    """
    addr: str = event_field('addr', 'address')
    hostname: str = event_field('hostname', 'bytes32', ascii_bytes=True)


@dataclass_json
@dataclass
class Post:
    """Content post model and event.

    Posts emitted by download service and consumed by the database service in order to store
    it in a persistent storage (to be accessible by web handlers).
    """
    magnet: str
    content: str
    created_at: int = None
