"""Peering service.

Main responsibilities:

* maintain collection of peers with help of PeerCollection
* ping peers and update their statuses
* gather new peers from neighbours
"""
import asyncio
import logging
from dataclasses import dataclass
from itertools import chain
from typing import List, Dict

from aiohttp_socks import ProxyError
from core_service import Service, listener

from ..events import NewPeer, DiscoveryRequest, DiscoveryFinished, DiscoveryFailed
from ..distance import ascii_to_hash_distance

from ..models import Peer
from .client import PeerClient, InvalidPeerResponse

log = logging.getLogger(__name__)


@dataclass
class DistributionTask:
    """Content distribution task definition.
    """
    filename: str
    magnet: str


class PeeringService(Service):

    """Sarafan peering service.

    Manage peer list and update their status. Provide discovery functionality.

    Consumes DiscoveryRequest events and produces DiscoveryResult events in response.

    Consumes NewPeer events to populate peers collection with new peers from blockchain.
    Internal peer collection also populated with peers found while discovering magnets
    and communicating with other nodes.

    Periodically update known peers status.
    """

    #: maximum number of in-memory peers
    max_peer_count: int = 1000
    #: peers by service_id
    peers: Dict[str, Peer]
    #: list of peers sorted by rating
    peers_by_rating: List[Peer]

    #: mapping of service id to client instance
    _peer_clients: Dict[str, PeerClient]
    #: bundle distribution queue
    _distribution_queue: asyncio.Queue

    def __init__(self, *, max_peer_count: int = 1000, **kwargs):
        super().__init__(**kwargs)

        self.max_peer_count = max_peer_count

        self.peers_by_rating = []
        self.peers = {}
        self._peer_clients = {}
        self._distribution_queue = asyncio.Queue()

    async def add_peer(self, peer: Peer):
        """Add peer to known network.
        """
        if peer.service_id in self.peers:
            log.warning("Peer %s already added", peer)
            return
        self.peers[peer.service_id] = peer
        self.peers_by_rating.append(peer)
        self.peers_by_rating.sort(key=lambda x: x.rating)
        await self._cleanup_peers()

    async def remove_peer(self, peer: Peer):
        """Remove peer from known network.
        """
        self.peers_by_rating.remove(peer)
        del self.peers[peer.service_id]

    def get_client(self, peer):
        """Get client instance for peer.

        TODO: cleanup unused clients or use single one
        """
        if not self.running or self.should_stop:
            raise RuntimeError("Should stop")
        client = self._peer_clients.get(peer.service_id)
        if not client:
            client = PeerClient(peer)
            self._peer_clients[peer.service_id] = client
        return client

    def peers_by_distance(self, magnet, max_count=max_peer_count):
        """Get peers list sorted by distance.

        `max_count` will limit the number of top rated nodes to account.
        """
        return sorted(filter(lambda x: x.rating > 0.1, self.peers_by_rating[:max_count]),
                      key=lambda x: ascii_to_hash_distance(x.service_id, magnet))

    async def distribute(self, filename, magnet):
        """Schedule distribution of provided content bundle.
        """
        await self.emit(DistributionTask(filename, magnet))

    @listener(DistributionTask)
    async def distribute_task(self, task_instance: DistributionTask):
        """Actually distribute bundle.
        """
        while True:
            peers = self.peers_by_distance(task_instance.magnet)
            if len(peers) == 0:
                log.warning("No peers found. Can't publish post, wait 10s and retry")
                await asyncio.sleep(10)
                continue

        # TODO: parallel upload
        success_upload_count = 0
        for peer in peers:
            client = self.get_client(peer)
            with open(task_instance.filename, 'rb') as fp:
                await client.upload(task_instance.magnet, fp)
            success_upload_count += 1
            if success_upload_count >= 10:
                break
        log.info("Content bundle %s distributed to %i nodes",
                 task_instance.magnet, success_upload_count)

    @listener(NewPeer)
    async def handle_new_peers(self, new_peer: NewPeer):
        """Listen for new peers from the blockchain.
        """
        self.log.debug("New peer received from contract %s", new_peer)
        peer = Peer(service_id=new_peer.hostname, address=new_peer.addr)
        await self.add_peer(peer)

    @listener(Peer)
    async def restored_peers_listener(self, peer: Peer):
        if peer.service_id not in self.peers:
            await self.add_peer(peer)

    @listener(DiscoveryRequest)
    async def handle_discovery_request(self, request: DiscoveryRequest):
        """DiscoveryRequest handler.

        Emit DiscoveryFinished in case of success and DiscoveryFailed in other case.
        """
        magnet = request.publication.magnet
        visited_peers = request.state.visited_peers
        max_depth = 25

        try:
            for _ in range(max_depth + 1):
                for i, peer in enumerate(self.peers_by_distance(magnet)):
                    if peer in visited_peers:
                        continue
                    visited_peers.add(peer)

                    client = self.get_client(peer)

                    try:
                        # TODO: we can check for magnet and discover in parallel
                        new_peers = await client.discover(magnet)
                        peer.rating *= 2
                        await self.emit(peer)
                        for p in chain(new_peers.match, new_peers.near):
                            if p.service_id not in self.peers:
                                await self.add_peer(p)
                        has_magnet = await client.has_magnet(magnet)
                        if has_magnet:
                            self.log.info("Peer %s found for magnet %s. DiscoveryFinished",
                                          peer, magnet)
                            await self.emit(DiscoveryFinished(
                                publication=request.publication,
                                peer=peer,
                                url=client.download_url(magnet),
                                state=request.state
                            ))
                            peer.rating = peer.rating * 2
                            await self.emit(peer)
                            return peer
                        else:
                            self.log.info("Peer %s has no magnet %s", peer, magnet)
                    except (InvalidPeerResponse, ProxyError):  # pragma: no cover
                        peer.rating = peer.rating / 4
                        await self.emit(peer)
                        continue
        finally:
            await self.emit(DiscoveryFailed(
                publication=request.publication,
                state=request.state
            ))

    async def _cleanup_peers(self):
        """Remove peers exceeding max peers limit.

        Peers with lowest rating will be removed.
        """
        peers_count = len(self.peers_by_rating)
        if peers_count > self.max_peer_count:
            delete_count = peers_count - self.max_peer_count
            self.log.debug("There are %i peers but %i is a maximum, need to delete %i peers",
                           peers_count, self.max_peer_count, delete_count)
            for p in self.peers_by_rating[:delete_count]:
                self.log.debug("Cleanup peer %s", p)
                await self.remove_peer(p)
