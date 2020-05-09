import sys

import configargparse

from core_service import Service, requirements

from sarafan.contract import ContractService

argparser = configargparse.get_argument_parser()
argparser.add_argument("--token", help="Sarafan token contract address",
                       default="0x957D0b2E4afA74A49bbEa4d7333D13c0b11af60F")


class Application(Service):
    def __init__(self, argv=None, **kwargs):
        super().__init__(**kwargs)
        self.argv = argv or sys.argv
        self.conf = argparser.parse_known_args(self.argv)[0]
        self.contract_service = ContractService(
            token_address=self.conf.token
        )

    @requirements()
    async def app_req(self):
        return [
            self.contract_service
        ]
