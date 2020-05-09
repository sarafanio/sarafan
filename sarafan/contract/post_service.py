from eth_account import Account
from eth_utils import to_checksum_address

from core_service import Service

from ..ethereum import Contract, EthereumNodeClient


class PostService(Service):
    """Sarafan client service responsible for content publication.
    """
    #: content contract
    content_contract: Contract
    #: Ethereum node client
    client: EthereumNodeClient

    def __init__(self, content_contract: Contract, node_client: EthereumNodeClient, **kwargs):
        super().__init__(**kwargs)
        self.client = node_client
        self.content_contract = content_contract

    async def post(self, address, private_key, reply_to, magnet, size, author, retention: int = 12):
        """Post new publication to content contract.

        :param address:
        :param private_key:
        :param reply_to:
        :param magnet:
        :param size:
        :param author:
        :param retention:
        :return:
        """
        tx_data = self.content_contract.call(
            'post', replyTo=reply_to, magnet=magnet, size=size, author=author, retention=retention
        )
        transaction = {
            'to': to_checksum_address(self.content_contract.address),
            'data': tx_data,
            'gas': 200000,
            'gasPrice': await self.client.gas_price(),
            'nonce': await self.client.get_transaction_count(address, "pending")
        }
        signed = Account.sign_transaction(transaction, private_key)
        await self.client.send_raw_transaction(signed.rawTransaction.hex())
