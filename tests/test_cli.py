from unittest.mock import patch

import pytest

from sarafan.cli import cli
from tests.utils import generate_rnd_address


@patch("sarafan.contract.service.ContractService._resolve_contract_address",
       return_value=generate_rnd_address())
def test_cli_simple(resolve_mock):
    with pytest.raises(SystemExit):
        cli(run_forever=False)
