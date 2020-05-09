from unittest.mock import patch, call

import pytest

from sarafan.app import Application


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
