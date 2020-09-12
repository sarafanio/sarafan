import pytest
import asyncio

from sarafan.events import NewPeer
from sarafan.models import Peer
from sarafan.peering import PeeringService, PeerClient

from .utils import generate_rnd_hash, generate_rnd_address


MAX_PEERS = 10


@pytest.fixture(name='peering')
async def peering_service():
    peering = PeeringService(max_peer_count=MAX_PEERS)
    await peering.start()
    try:
        yield peering
    finally:
        await peering.stop()


@pytest.mark.asyncio
async def test_add_peer(peering):
    peer = Peer(service_id='fakepeer1')
    await peering.add_peer(peer)
    await peering.add_peer(peer)  # check duplicates
    peers_list = list(peering.peers_by_distance(generate_rnd_hash()))
    assert len(peers_list) == 1
    assert peer in peers_list


@pytest.mark.asyncio
async def test_remove_peer(peering):
    peer = Peer(service_id='removepeer1')
    await peering.add_peer(peer)
    client = peering.get_client(peer)
    assert isinstance(client, PeerClient)
    await peering.remove_peer(peer)
    peers_list = list(peering.peers_by_distance(generate_rnd_hash()))
    assert len(peers_list) == 0


@pytest.mark.asyncio
async def test_handle_new_peer_event(peering):
    new_peer_event = NewPeer(
        addr=generate_rnd_address(),
        hostname='new_peer'
    )
    await peering.dispatch(new_peer_event)
    peers_list = list(peering.peers_by_distance(generate_rnd_hash()))
    assert len(peers_list) == 1
    assert peers_list[0].address == new_peer_event.addr
    assert peers_list[0].service_id == new_peer_event.hostname


@pytest.mark.asyncio
async def test_peer_cleanup(peering):
    first_peer = None
    for i in range(MAX_PEERS + 1):
        peer = Peer(service_id=f'peer{i}', rating=i * 0.01)
        if first_peer is None:
            first_peer = peer
        await peering.add_peer(peer)

    peers_list = list(peering.peers.values())
    assert len(peers_list) == MAX_PEERS
    assert first_peer not in peers_list
