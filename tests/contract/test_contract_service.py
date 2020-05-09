from unittest import mock

import pytest
from eth_abi import encode_single

from sarafan.contract import ContractService


@pytest.mark.asyncio
async def test_contract_service_simple():
    service = ContractService(
        token_address="0xd5e64d2103A265ece8E0afF188F9549Df6E70A20",
        content_address="0xd5e64d2103A265ece8E0afF188F9549Df6E70A20",
        peering_address="0xd5e64d2103A265ece8E0afF188F9549Df6E70A20"
    )
    await service.start()
    await service.stop()


@pytest.mark.asyncio
async def test_address_resolution():
    service = ContractService(
        token_address="0xd5e64d2103A265ece8E0afF188F9549Df6E70A20",
    )
    fake_address = "0xd5e64d2103A265ece8E0afF188F9549Df6E70A20"
    fake_contract_response = '0x' + encode_single("address", bytes.fromhex(fake_address[2:])).hex()
    with mock.patch.object(service.eth, "call", return_value=fake_contract_response):
        await service.start()
        assert service.content_address == fake_address
        assert service.peering_address == fake_address
        await service.stop()
