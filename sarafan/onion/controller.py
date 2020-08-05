import asyncio
from pathlib import Path
from typing import Optional

from stem.control import Controller
from core_service import Service, task


class HiddenServiceController(Service):
    """Controller for single hidden service instance.

    Will create new ephemeral hidden service
    """
    controller: Controller

    name: str
    state_file: str
    private_key: str = 'BEST'
    private_key_type: str = 'NEW'
    service_id: Optional[str] = None
    service_id_future: asyncio.Future

    service_created = False

    def __init__(self, name, controller, ports, **kwargs):
        self.name = name
        self.ports = ports
        self.controller = controller
        super().__init__(**kwargs)
        self.service_id_future = self.loop.create_future()

    async def start(self):
        await super().start()

        self.log.info("Creating ephemeral hidden service for %s ...", self.name)
        if self.private_key_type == 'NEW':
            self.log.warning("Starting new hidden service for `%s`", self.name)
        else:
            self.log.debug("Starting with existing private key (%s)", self.private_key_type)

        result = self.controller.create_ephemeral_hidden_service(
            ports=self.ports,
            detached=True,
            await_publication=False,
            key_content=self.private_key,
            key_type=self.private_key_type,
        )
        self.service_created = True
        if self.private_key_type == 'NEW':
            self.private_key = result.private_key
            self.private_key_type = result.private_key_type
        self.service_id = result.service_id
        self.service_id_future.set_result(result.service_id)
        self.log.warning("Hidden service address for `%s` service: %s.onion", self.name, self.service_id)

    async def stop(self):
        if self.service_created:
            self.log.info("Removing ephemeral hidden service %s...", self.name)
            self.controller.remove_ephemeral_hidden_service(self.service_id)
        self.controller.close()
        await super().stop()
