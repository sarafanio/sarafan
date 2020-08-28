from typing import Optional

from eth_abi import decode_single

from core_service import Service, requirements
from eth_utils import to_checksum_address

from .post_service import PostService
from ..ethereum import Contract, EthereumNodeClient
from .abi import CONTENT_CONTRACT, PEERING_CONTRACT, TOKEN_CONTRACT
from .event_service import ContractEventService


class ContractService(Service):
    """Sarafan contract service.

    Manage a collection of ContractEventServices. Resolve child contract addresses
    from token contract if necessary.
    """
    eth: EthereumNodeClient

    #: content posting service
    post_service: PostService
    #: peer announcement service
    # announcement_service:

    # contract services
    token: ContractEventService
    content: Optional[ContractEventService] = None
    peering: Optional[ContractEventService] = None

    # contract addresses
    token_address: str
    content_address: Optional[str] = None
    peering_address: Optional[str] = None

    _resolved: bool = False

    def __init__(self,
                 token_address: str,
                 content_address: Optional[str] = None,
                 peering_address: Optional[str] = None,
                 eth_client: Optional[EthereumNodeClient] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.token_address = token_address
        self.content_address = content_address
        self.peering_address = peering_address

        if eth_client is None:
            eth_client = EthereumNodeClient()
        self.eth = eth_client

    async def resolve(self):
        """Resolve content and peering contract addresses from Sarafan token.

        Should be called before start.
        """
        self.create_token_service()

        if not self.content_address:
            self.content_address = await self._resolve_contract_address('getContentContract')
        await self.create_content_service()

        if not self.peering_address:
            self.peering_address = await self._resolve_contract_address('getPeeringContract')
        await self.create_peering_service()

        self._resolved = True

    async def start(self):
        if not self._resolved:
            await self.resolve()
            self.log.warning("Contract service didn't resolved before the start")
        await super().start()

    @requirements()
    async def contract_service_req(self):
        return [
            self.token,
            self.peering,
            self.content,
        ]

    @requirements('contract_service_req')
    async def post_service_req(self):
        await self.create_post_service()
        return [
            self.post_service
        ]

    def create_token_service(self):
        """Create token contract service instance.
        """
        if hasattr(self, 'token'):  # pragma: nocover
            raise RuntimeError("Token service already created")
        self.token = ContractEventService(
            self.eth, Contract(self.token_address, TOKEN_CONTRACT['abi'])
        )
        self.log.debug("Token ContractEventService created")

    async def create_content_service(self):
        """Create content contract service instance.

        Content contract address will be resolved if it is not provided.
        """
        if self.content is not None:  # pragma: nocover
            raise RuntimeError("Content service already created")
        if self.content_address is None:
            self.content_address = await self._resolve_contract_address('getContentContract')
        self.content = ContractEventService(
            self.eth, Contract(self.content_address, CONTENT_CONTRACT['abi'])
        )
        self.log.debug("Content ContractEventService created")

    async def create_peering_service(self):
        """Create peering contract service instance.

        Peering contract address will be resolved if it is not provided.
        """
        if self.peering is not None:  # pragma: no cover
            raise RuntimeError("Peering services already created")
        if self.peering_address is None:
            self.peering_address = await self._resolve_contract_address('getPeeringContract')
        self.peering = ContractEventService(
            self.eth,
            Contract(self.peering_address, PEERING_CONTRACT['abi'])
        )
        self.log.debug("Peering ContractEventService created")

    async def create_post_service(self):
        if getattr(self, 'post_service', False):  # pragma: no cover
            raise RuntimeError("Post service already created")
        self.post_service = PostService(
            content_contract=self.content.contract,
            node_client=self.eth,
        )
        self.log.debug("PostService instance created")

    async def _resolve_contract_address(self, method_name) -> str:
        """Resolve related contract address from main contract property.

        :param method_name: name of the abi method/property
        :raise RuntimeError: if address can't be resolved
        :return:
        """
        res = await self.eth.call({
            "to": self.token.contract.address,
            "data": '0x%s' % self.token.contract.call(method_name).hex(),
        })
        if res == '0x':
            self.log.error("Can't resolve %s %s", method_name, self.token.contract.address)
            raise Exception("Can't resolve contract address from method %s "
                            "contract return 0x (looks like a wrong token contract "
                            "address %s)" % (method_name, self.token.contract.address))
        address = to_checksum_address(decode_single('address', bytes.fromhex(res[2:])))
        self.log.debug("Contract address %s resolved from %s method", address, method_name)
        return address
