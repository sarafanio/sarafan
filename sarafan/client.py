"""Sarafan peering network client.

Allows to discover and download content.
"""
import asyncio
import logging
import os
import random
import shutil
from pathlib import Path
from typing import List, Union, Dict

from Cryptodome.Hash import keccak
from aiohttp import StreamReader

from .distance import ascii_to_hash, ascii_to_hash_distance
from .events import Peer
from .magnet import magnet_path
from .peering import PeerClient
from .peering.client import InvalidChecksum, DiscoveryResult, InvalidPeerResponse

log = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


class UploadError(Exception):
    pass


class PeerCollection:
    # map service id to peer instance
    _peers: Dict[str, Peer]
    _by_rating: List[Peer]
    #: maximum number of in-memory peers
    _max_peer_count: int = 1000

    def __init__(self, peers: Union[List[Peer], List[str]], max_peer_count: int = 1000):
        self._max_peer_count = max_peer_count
        self._peers = {}
        self._by_rating = []
        for peer in peers:
            self.add(peer)

    def add(self, peer: Union[Peer, str]) -> Peer:
        """Add peer to collection.

        Already existing peer instance will be returned in case of peer with
        such service_id exists.
        """
        if isinstance(peer, str):
            if peer.endswith('.onion'):
                peer = peer[:-6]
            if peer in self._peers:
                # return already saved instance
                return self._peers[peer]
            peer = Peer(service_id=peer, rating=0.5)
        elif isinstance(peer, Peer):
            if peer.service_id in self._peers:
                # return already saved instance
                return self._peers[peer.service_id]
        else:
            raise TypeError("Unsupported peer type %s (should be Peer or service id)"
                            % type(peer))
        if peer.service_id in self._peers:
            log.warning("Peer %s already added", peer)
            return peer
        self._peers[peer.service_id] = peer
        self._by_rating.append(peer)
        self._by_rating.sort(key=lambda x: x.rating)
        log.info("Add peer %s", peer)
        self._cleanup_peers()
        return peer

    def remove(self, peer: Union[Peer, str]):
        service_id = peer
        if isinstance(peer, Peer):
            service_id = peer.service_id
        self._by_rating.remove(self._peers[service_id])
        del self._peers[service_id]

    def nearest(self, magnet: str, max_count=_max_peer_count) -> List[Peer]:
        """Return list of nearest peers sorted by distance (closest first).

        :param magnet:
        :param max_count:
        """
        return sorted(self._by_rating[:max_count],
                      key=lambda x: ascii_to_hash_distance(x.service_id, magnet))

    def neighbours(self, service_id: str) -> List[Peer]:
        return self.nearest(ascii_to_hash(service_id))

    def _cleanup_peers(self):
        """Remove peers exceeding max peers limit.

        Peers with lowest rating will be removed.
        """
        peers_count = len(self._by_rating)
        if peers_count > self._max_peer_count:
            delete_count = peers_count - self._max_peer_count
            log.debug("There are %i peers but %i is a maximum, need to delete %i peers",
                      peers_count, self._max_peer_count, delete_count)
            for p in self._by_rating[:delete_count]:
                log.debug("Cleanup peer %s", p)
                self.remove(p)


class SarafanClient:
    def __init__(self,
                 bootstrap_peers: Union[List[Peer], List[str], PeerCollection],
                 proxy: str = "socks5://127.0.0.1:9050",
                 content_path: str = './content',
                 loop=None):
        if not isinstance(bootstrap_peers, PeerCollection):
            log.info("Create peer collection %s", bootstrap_peers)
            bootstrap_peers = PeerCollection(bootstrap_peers)
        self.peers = bootstrap_peers
        self.proxy = proxy
        self.content_path = Path(content_path)
        self._loop = loop

    @property
    def loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    async def download(self, magnet):  # noqa: C901
        peers_list = self.peers.nearest(magnet)
        visited_peers = set()
        log.info("Start download %s from peers list %s", magnet, peers_list)
        while peers_list:
            current_list = peers_list[:]
            has_magnet_tasks = []
            clients = {}
            # invoke has_magnet on each client
            for peer in current_list:
                client = clients[peer.service_id] = PeerClient(peer, self.proxy)
                has_magnet_tasks.append(self.loop.create_task(
                    client.has_magnet(magnet)
                ))
                log.debug("Try to download %s from %s", magnet, peer)
            results = await asyncio.gather(*has_magnet_tasks, return_exceptions=True)

            # check peers with magnet found and invoke discovery on other peers
            discovery_tasks = []
            discovery_peers = []
            for i, item in enumerate(results):
                peer = current_list[i]
                client = clients[peer.service_id]
                if item:
                    try:
                        download_path = await client.download(magnet, self._store)
                        for t in discovery_tasks:
                            t.cancel()
                        return download_path
                    except DownloadError:
                        # just go to the next results
                        # TODO: decrease peer rating because it reported magnet exist
                        log.debug("Download error from peer %s while downloading %s",
                                  peer, magnet)
                else:
                    log.debug("Scheduler discovery for %s", peer)
                    discovery_peers.append(peer)
                    discovery_tasks.append(self.loop.create_task(client.discover(magnet)))

            # clear peers list
            visited_peers = visited_peers.union(peers_list)
            peers_list = []

            # parse discovery results
            discovery_results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
            for i, result in enumerate(discovery_results):
                peer = discovery_peers[i]
                # FIXME: change peer rating and fill peers list
                if isinstance(result, DiscoveryResult):
                    log.debug("New peers from discovery: %s", result)
                    peers_list.extend(result.match + result.near)
                elif isinstance(result, InvalidPeerResponse):
                    peer.rating /= 2
                    log.debug("Invalid response from %s. Rating decreased.", peer)
                else:
                    log.debug("Strange discovery result: %s", type(result))

            for client in clients.values():
                await client.close()
        raise DownloadError("Content not found in the network")

    async def upload(self, magnet, local_path, peers_count=10, min_peers_count=2):
        success_count = 0
        for peer in self.peers.nearest(magnet):
            client = PeerClient(peer, self.proxy)
            try:
                await client.upload(magnet, local_path)
                success_count += 1
                if success_count >= peers_count:
                    break
            except UploadError:
                pass  # FIXME
        if success_count < min_peers_count:
            raise Exception  # FIXME

    async def _store(self, magnet: str, content: StreamReader, chunk_size=1024):
        """Check and store content file.

        :param magnet:
        :param content:
        :param chunk_size:
        :return:
        """
        to_path = self.get_absolute_path(magnet)
        tmp_content_path = ''.join([str(to_path), 'tmp.%s' % random.randint(10000, 99999)])
        check = keccak.new(digest_bytes=32)

        try:
            with open(tmp_content_path, 'wb') as fd:
                async for chunk, _ in content.iter_chunks():
                    fd.write(chunk)
                    check.update(data=chunk)

            checksum = check.hexdigest()
            if checksum != magnet:
                log.error("Downloaded content file %s checksum %s didn't match", magnet, checksum)
                raise InvalidChecksum(magnet, checksum)
            shutil.move(tmp_content_path, to_path)
            return to_path
        finally:
            os.unlink(tmp_content_path)

    def get_absolute_path(self, magnet) -> Path:
        return self.content_path / magnet_path(magnet)
