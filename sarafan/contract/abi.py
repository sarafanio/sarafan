"""Preloaded Sarafan contracts ABIs.

>>> from sarafan.contract import abi
>>> 'abi' in abi.TOKEN_CONTRACT
True
>>> 'abi' in abi.CONTENT_CONTRACT
True
>>> 'abi' in abi.PEERING_CONTRACT
True
"""
import json
from pathlib import Path


BASE_PATH = Path(__file__).parent.parent.parent / "abi"


def load_contract_json(filename):
    with open(BASE_PATH / filename, "r") as fp:
        return json.load(fp)


TOKEN_CONTRACT = load_contract_json("SarafanToken.json")
CONTENT_CONTRACT = load_contract_json("SarafanContent.json")
PEERING_CONTRACT = load_contract_json("SarafanPeering.json")
