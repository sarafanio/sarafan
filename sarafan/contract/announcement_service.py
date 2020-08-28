from core_service import Service, task
from eth_account import Account
from eth_utils import to_checksum_address

from ..ethereum import EthereumNodeClient
from ..onion.controller import HiddenServiceController


class AnnouncementService(Service):
    """Announce node with NewPeer blockchain event.
    """
    eth_client: EthereumNodeClient
    onion_service: HiddenServiceController

    def __init__(self,
                 *args,
                 peering_contract,
                 node_account,
                 node_private_key,
                 hidden_service: HiddenServiceController,
                 eth_client: EthereumNodeClient = None,
                 **kwargs):
        self.peering_contract = peering_contract
        self.node_account = node_account
        self.node_private_key = node_private_key
        self.hidden_service = hidden_service
        if eth_client is None:
            eth_client = EthereumNodeClient()
        self.eth_client = eth_client
        super().__init__(*args, **kwargs)

    @task(periodic=False)
    async def announce_peer(self):
        self.log.debug("Waiting for hidden service address to announce")
        service_id = await self.hidden_service.get_service_id()
        self.log.debug("Service id %s received", service_id)
        tx_data = self.peering_contract.call(
            'register', hostname=bytes(service_id, 'ascii')
        )
        transaction = {
            'to': to_checksum_address(self.peering_contract.address),
            'data': tx_data,
            'gas': 200000,
            'gasPrice': await self.eth_client.gas_price(),
            'nonce': await self.eth_client.get_transaction_count(self.node_account, "pending")
        }
        signed = Account.sign_transaction(transaction, self.node_private_key)
        await self.eth_client.send_raw_transaction(signed.rawTransaction.hex())
