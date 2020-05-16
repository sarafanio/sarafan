import asyncio
from unittest.mock import patch, call

import pytest

from sarafan.app import Application

from .utils import generate_rnd_address


@pytest.mark.asyncio
@patch("sarafan.app.ContractService._resolve_contract_address")
async def test_app_simple(resolve_mock):
    app = Application()
    await app.start()
    resolve_mock.assert_has_calls([
        call('getContentContract'),
        call('getPeeringContract')
    ])
    await app.stop()


@pytest.mark.asyncio
@patch("sarafan.contract.service.ContractService._resolve_contract_address",
       return_value=generate_rnd_address())
@patch("sarafan.contract.service.EthereumNodeClient.get_logs", return_value=[])
@patch("sarafan.contract.service.EthereumNodeClient.block_number", side_effect=[0, 1, 2])
async def test_process_new_publications(
    resolve_mock,
    get_logs_mock,
    block_number_mock,
    rnd_address,
    rnd_hash
):
    app = Application()
    await app.start()
    Publication = app.contract.content.contract.event('Publication')
    pub = Publication(reply_to=rnd_hash()[2:], magnet=rnd_hash()[2:], source=rnd_address(), size=1024, retention=12)
    await app.publications_queue.put(pub)
    await asyncio.sleep(0)
    assert app.running
    await app.stop()
