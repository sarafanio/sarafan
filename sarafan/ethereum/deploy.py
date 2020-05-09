"""Sarafan contract deployment utils.

Should be used for development and testing only.
"""
import asyncio
import logging
from collections import namedtuple

from eth_abi import encode_abi
from eth_account.account import LocalAccount
from eth_utils import to_checksum_address

from ..contract.abi import TOKEN_CONTRACT, CONTENT_CONTRACT, PEERING_CONTRACT

from .client import EthereumNodeClient

from .contract import Contract

log = logging.getLogger(__name__)


SarafanContracts = namedtuple("SarafanContracts", ("token", "content", "peering"))


async def deploy_sarafan_contracts(
    client: EthereumNodeClient, from_account: LocalAccount
) -> SarafanContracts:
    """Deploy and link sarafan contracts.
    """
    token_contract = Contract(
        await deploy_single_contract(client, from_account, TOKEN_CONTRACT["bytecode"]),
        TOKEN_CONTRACT["abi"],
    )

    # token address should be passed to other contracts as CTOR single argument
    child_args = encode_abi(["address"], [token_contract.address]).hex()

    content_contract = Contract(
        await deploy_single_contract(
            client, from_account, CONTENT_CONTRACT["bytecode"] + child_args
        ),
        CONTENT_CONTRACT["abi"],
    )
    peering_contract = Contract(
        await deploy_single_contract(
            client, from_account, PEERING_CONTRACT["bytecode"] + child_args
        ),
        PEERING_CONTRACT["abi"],
    )

    contracts = SarafanContracts(
        token=token_contract, content=content_contract, peering=peering_contract
    )

    await link_deployed_contracts(client, from_account, contracts)

    return contracts


async def link_deployed_contracts(
    client: EthereumNodeClient, from_account: LocalAccount, contracts: SarafanContracts
):
    """Link deployed contracts.
    """
    token = contracts.token

    code = token.call("setContentContract", contracts.peering.address)

    tx_obj = {
        "from": from_account.address,
        "to": str(to_checksum_address(token.address)),
        "gas": 100000,
        "data": code,
        "gasPrice": await client.gas_price(),
        "nonce": await client.get_transaction_count(from_account.address, "pending"),
    }
    await client.send_raw_transaction(
        from_account.sign_transaction(tx_obj).rawTransaction.hex()
    )

    code = token.call("setPeeringContract", contracts.peering.address)

    tx_obj = {
        "from": from_account.address,
        "to": str(to_checksum_address(token.address)),
        "gas": 100000,
        "data": code,
        "gasPrice": await client.gas_price(),
        "nonce": await client.get_transaction_count(from_account.address, "pending"),
    }
    await client.send_raw_transaction(
        from_account.sign_transaction(tx_obj).rawTransaction.hex()
    )


async def deploy_single_contract(
    client: EthereumNodeClient, from_account: LocalAccount, contract_code: str
) -> str:
    """Deploy smart-contract and return address.
    """
    estimate_gas = await client.estimate_gas(from_account.address, str(contract_code))
    logging.debug("Estimated gas for contract deployment: %s", estimate_gas)

    tx_obj = {
        "from": from_account.address,
        "gas": hex(estimate_gas),
        "data": contract_code,
        "gasPrice": await client.gas_price(),
        "nonce": await client.get_transaction_count(from_account.address, "pending"),
    }
    signed = from_account.sign_transaction(tx_obj)
    tx_hash = await client.send_raw_transaction(signed.rawTransaction.hex())
    log.debug("Contract TX hash: %s", tx_hash)

    while True:
        receipt = await client.get_transaction_receipt(tx_hash)
        if receipt and receipt.get("blockHash"):
            log.debug("Contract transaction successfully mined.")
            break
        log.warning("Wait transaction mined. Sleep %ss...", 10)
        await asyncio.sleep(10)

    contract_address = receipt["contractAddress"]

    log.debug("Deployed contract address: %s", contract_address)
    return contract_address
