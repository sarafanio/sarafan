"""Simple Ethereum node client implementation.

Minimal functionality used by Sarafan.
"""
import logging
from typing import List, Optional, Any, Dict

from aiohttp import ClientSession

from .exceptions import EXCEPTIONS_MAP, EthereumNodeException
from .event import Event

log = logging.getLogger(__name__)


class EthereumNodeClient:
    """Ethereum node client.

    Utilise ethereum node standard JSON-RPC interface.
    """

    def __init__(self, node_url: str = "http://127.0.0.1:7545/"):
        self.node_url = node_url
        self._session = ClientSession()

    @property
    def closed(self):
        """Check if client was closed.
        """
        return self._session.closed

    async def close(self):
        """Close client and free resources.
        """
        await self._session.close()

    async def block_number(self) -> int:
        """Get last block number.
        """
        res = await self.request("eth_blockNumber")
        return int(res.get("result"), 16)

    async def chain_id(self) -> int:
        """Get current chain id.
        """
        data = await self.request("eth_chainId")
        return int(data.get("result"), 16)

    async def accounts(self) -> List[str]:
        res = await self.request('eth_accounts')
        return res.get('result', [])

    async def get_logs(
        self,
        address: str,
        from_block: int,
        to_block: Optional[int] = None,
        topics: Optional[List[str]] = None,
    ) -> List[Event]:
        """Get contract event logs.

        :param address: contract address
        :param from_block: starting block number
        :param to_block: end block number or None for latest
        :param topics: list of topics to filter events
        """
        params: Dict[str, Any] = {
            "fromBlock": hex(from_block),
            "address": address,
        }
        if to_block:
            params["toBlock"] = hex(to_block)
        if topics:
            params["topics"] = topics
        data = await self.request("eth_getLogs", [params])
        return [Event.from_raw_event(raw_event) for raw_event in data.get("result")]

    async def get_transaction_count(self, address, tag=None) -> int:
        """Get number of transactions for specific address.
        """
        params = [address]
        if tag:
            params.append(tag)
        data = await self.request("eth_getTransactionCount", params)
        return int(data.get("result"), 16)

    async def gas_price(self) -> int:
        """Get current gas price.
        """
        data = await self.request("eth_gasPrice")
        return int(data.get("result"), 16)

    async def estimate_gas(self, from_address: str, code: str, to: str = None) -> int:
        """Estimate gas for transaction execution.
        """
        params = {"from": from_address, "data": code}
        if to:
            params["to"] = to
        data = await self.request("eth_estimateGas", [params])
        res = data.get("result")
        try:
            if res is not None:
                return int(res[2:], 16)
            log.error("Empty result for eth_estimateGas")
            raise EthereumNodeException("Gas estimation error")
        except (ValueError, TypeError):
            log.error("Wrong eth_estimateGas response (not an int): %s", res)
            raise EthereumNodeException("Wrong estimate gas response")

    async def send_transaction(self, tx_object):
        """Send transaction and return transaction hash.

        FIXME: unused
        """
        data = await self.request("eth_sendTransaction", [tx_object])
        return data.get("result")

    async def call(self, tx_object):
        data = await self.request('eth_call', [tx_object])
        return data.get('result')

    async def send_raw_transaction(self, tx_object) -> str:
        """Send raw transaction and return transaction hash.
        """
        data = await self.request("eth_sendRawTransaction", [tx_object])
        return data.get("result")

    async def get_transaction_receipt(self, tx_hash: str):
        """Retrieve transaction receipt from node.
        """
        data = await self.request("eth_getTransactionReceipt", [tx_hash])
        return data.get("result")

    async def request(self, method, params=None):
        """Send request to ethereum node.

        :param method: RPC method name
        :param params: params
        :return: RPC response
        """
        # if self._session.closed:  # pragma: no cover
        #     log.warning("HTTP client session is closed, request interrupted")
        #     return
        log.debug("Ethereum node request method `%s`, params: %s", method, params)
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            request_body["params"] = params

        async with ClientSession() as session:
            resp = await session.post(
                self.node_url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            data = await resp.json()

        log.debug("Ethereum node response: %s", data)
        if "error" in data:
            message = data["error"].get("message")
            log.error(
                "Ethereum node request to method `%s` with params `%s`"
                "failed with error: %s",
                method,
                params,
                data["error"],
            )
            if message in EXCEPTIONS_MAP:
                cls = EXCEPTIONS_MAP[message]
                raise cls()
            raise EthereumNodeException()
        return data
