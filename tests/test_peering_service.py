from typing import AsyncGenerator
from unittest import mock

import pytest
from async_timeout import timeout

from sarafan.events import NewPeer, DiscoveryRequest, Publication, DiscoveryFinished, DiscoveryFailed
from sarafan.models import Peer
from sarafan.peering import PeeringService, PeerClient
from sarafan.peering.client import DiscoveryResult

from .utils import generate_rnd_hash, generate_rnd_address


MAX_PEERS = 10


@pytest.fixture(name='peering')
async def peering_service() -> AsyncGenerator[PeeringService, None]:
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
    await client.close()


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


@pytest.mark.asyncio
@mock.patch('sarafan.peering.service.PeerClient.has_magnet', side_effect=[True])
@mock.patch('sarafan.peering.service.PeerClient.discover', return_value=DiscoveryResult())
async def test_handle_discovery_request(has_magnet_mock, discover_mock, peering: PeeringService):
    peer = Peer(service_id='fake_discovery')
    await peering.add_peer(peer)
    publication = Publication(
        reply_to='0x',
        magnet=generate_rnd_hash()[2:],
        source=generate_rnd_address(),
        size=1,
        retention=1
    )
    discovery_request = DiscoveryRequest(publication=publication)
    service_bus = peering.bus
    queue = service_bus.subscribe(DiscoveryFinished)
    await peering.dispatch(discovery_request)
    with timeout(1):
        event: DiscoveryFinished = await queue.get()
        assert event.publication == publication
    assert has_magnet_mock.called_once()


@pytest.mark.asyncio
@mock.patch('sarafan.peering.service.PeerClient.has_magnet', side_effect=[False])
@mock.patch('sarafan.peering.service.PeerClient.discover', return_value=DiscoveryResult())
async def test_discovery_failed(has_magnet_mock, discover_mock, peering: PeeringService):
    peer = Peer(service_id="fail_discovery")
    await peering.add_peer(peer)
    publication = Publication(
        reply_to='0x',
        magnet=generate_rnd_hash()[2:],
        source=generate_rnd_address(),
        size=1,
        retention=1
    )
    discovery_request = DiscoveryRequest(publication=publication)
    service_bus = peering.bus
    queue = service_bus.subscribe(DiscoveryFailed)
    await peering.dispatch(discovery_request)
    with timeout(1):
        event: DiscoveryFailed = await queue.get()
        assert event.publication == publication
    assert has_magnet_mock.called_once()
