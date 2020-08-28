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
from typing import List, Dict, AsyncGenerator

from aiohttp_socks import ProxyError
from core_service import Service, task

from ..distance import ascii_to_hash_distance

from .peer import Peer
from .client import PeerClient, InvalidPeerResponse

log = logging.getLogger(__name__)


class MagnetNotDiscovered(Exception):
    pass


@dataclass
class DistributionTask:
    filename: str
    magnet: str


class PeeringService(Service):
    """Sarafan p2p network service.

    Manage peer list and update their status. Provide discovery functionality.
    """
    #: maximum number of in-memory peers
    max_peer_count: int = 1000
    #: peers by service_id
    peers: Dict[str, Peer]
    #: list of peers sorted
    peers_by_rating: List[Peer]

    #: mapping of service id to client instance
    _peer_clients: Dict[str, PeerClient]
    #: bundle distribution queue
    _distribution_queue: asyncio.Queue

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        if peer.service_id in self._peer_clients:
            client = self._peer_clients[peer.service_id]
            if not client.closed:
                await client.close()

    def get_client(self, peer):
        """Get client instance for peer.

        TODO: cleanup unused clients or use single one
        """
        client = self._peer_clients.get(peer.service_id)
        if not client:
            client = PeerClient(peer)
            self._peer_clients[peer.service_id] = client
        return client

    def peers_by_distance(self, magnet, max_count=max_peer_count):
        """Get peers list sorted by distance.

        `max_count` will limit the number of top rated nodes to account.
        """
        return sorted(self.peers_by_rating[:max_count],
                      key=lambda x: ascii_to_hash_distance(x.service_id, magnet))

    async def discover(self, magnet: str, max_depth: int = 20) -> AsyncGenerator[PeerClient, None]:
        """Search for magnet location.

        0. Check if we know more than one peer
        1. Get nearest peer from already known
        2a. Request peer for content
        3b. Request list of other peers
        2. return service id containing file or repeat while no new peers received
        3. raise MagnetNotDiscovered if service id not found and there is no new peers to discover
        """
        visited_peers = set()
        for _ in range(max_depth + 1):
            for i, peer in enumerate(self.peers_by_distance(magnet)):
                if peer in visited_peers:
                    continue
                visited_peers.add(peer)

                client = self.get_client(peer)

                try:
                    has_magnet = await client.has_magnet(magnet)
                    if has_magnet:
                        yield peer

                    new_peers = await client.discover(magnet)
                except (InvalidPeerResponse, ProxyError):
                    continue

                for p in chain(new_peers.match, new_peers.near):
                    if p.service_id not in self.peers:
                        await self.add_peer(p)

        raise MagnetNotDiscovered("Reach limit of network search depth")

    async def distribute(self, filename, magnet):
        """Schedule distribution of provided content bundle.
        """
        await self._distribution_queue.put(
            DistributionTask(filename, magnet)
        )

    @task()
    async def _distribute_task(self):
        """Actually distribute bundle.
        """
        task = await self._distribution_queue.get()

        while True:
            peers = self.peers_by_distance(task.magnet)
            if len(peers) == 0:
                log.warning("No peers found. Can't publish post, wait 10s and retry")
                await asyncio.sleep(10)
                continue

        # TODO: parallel upload
        success_upload_count = 0
        for peer in peers:
            client = self.get_client(peer)
            with open(task.filename, 'rb') as fp:
                await client.upload(task.magnet, fp)
            success_upload_count += 1
            if success_upload_count >= 10:
                break
        log.info("Content bundle %s distributed to %i nodes",
                 task.magnet, success_upload_count)

    async def _cleanup_peers(self):
        """Remove peers exceeding max peers limit.

        Peers with lowest rating will be removed.
        """
        peers_count = len(self.peers_by_rating)
        if peers_count > self.max_peer_count:
            delete_count = -peers_count - self.max_peer_count
            for p in self.peers_by_rating[-delete_count:]:
                await self.remove_peer(p)
