import asyncio
from unittest import mock

import pytest
from async_timeout import timeout

from sarafan.contract.event_service import ContractEventService
from sarafan.ethereum import EthereumNodeClient, Contract, Event
from sarafan.contract.abi import CONTENT_CONTRACT
from sarafan.ethereum.block_range import BlockRange


def rnd_hash(digest_bytes=32):
    from Cryptodome.Hash import keccak
    from random import randint
    return "0x%s" % keccak.new(
        data=b'%i' % randint(0, 10000),
        digest_bytes=digest_bytes
    ).hexdigest()


def rnd_address():
    return str(rnd_hash(28)[:42])


@pytest.mark.asyncio
async def test_contract_event_service_simple():
    node_client = EthereumNodeClient()
    contract = Contract(
        address="0x49Da5D877830AA2534b3C6701e2fF6bA655C6Ab7",
        abi=CONTENT_CONTRACT['abi']
    )

    service = ContractEventService(
        node_client=node_client,
        contract=contract
    )
    queue = service.subscribe(contract.event('Publication'))
    assert isinstance(queue, asyncio.Queue)

    Publication = contract.event('Publication')

    pub = Publication(reply_to=b'123', magnet=b'123', source=rnd_address(), size=1024, retention=12)
    logs = [
        [
            Event(log_index=0,
                  block_number=0,
                  block_hash=rnd_hash(),
                  transaction_hash=rnd_hash(),
                  transaction_index=0,
                  address="0x49Da5D877830AA2534b3C6701e2fF6bA655C6Ab7",
                  data=pub.data(),
                  topics=pub.topics())
        ],
    ]
    with mock.patch.object(node_client, 'get_logs', side_effect=logs), \
            mock.patch.object(node_client, 'block_number', side_effect=[0, 1, 2]):
        await service.start()
        async with timeout(1):
            pub = await queue.get()
        assert pub.reply_to.rstrip(b'\x00') == b'123'
        await service.stop()


@pytest.mark.parametrize('reverse_order', [True, False])
@pytest.mark.asyncio
async def test_contract_event_block_range(reverse_order):
    node_client = EthereumNodeClient()
    contract = Contract(
        address="0x49Da5D877830AA2534b3C6701e2fF6bA655C6Ab7",
        abi=CONTENT_CONTRACT['abi']
    )

    service = ContractEventService(
        node_client=node_client,
        contract=contract,
        block_range=BlockRange(
            from_block=0,
            to_block=1,
            reverse=reverse_order
        )
    )
    queue = service.subscribe(contract.event('Publication'))
    assert isinstance(queue, asyncio.Queue)

    Publication = contract.event('Publication')

    pub = Publication(reply_to=b'123', magnet=b'123', source=rnd_address(), size=1024, retention=12)
    logs = [
        [
            Event(log_index=0,
                  block_number=0,
                  block_hash=rnd_hash(),
                  transaction_hash=rnd_hash(),
                  transaction_index=0,
                  address="0x49Da5D877830AA2534b3C6701e2fF6bA655C6Ab7",
                  data=pub.data(),
                  topics=pub.topics())
        ],
        [],
        [],
    ]
    with mock.patch.object(node_client, 'get_logs', side_effect=logs), \
            mock.patch.object(node_client, 'block_number', side_effect=[0, 1, 2]):
        await service.start()
        async with timeout(1):
            pub = await queue.get()
        assert pub.reply_to.rstrip(b'\x00') == b'123'
        await service.stop()
