import asyncio
import socket
from pathlib import Path
from typing import Optional

from stem.control import Controller
from core_service import Service, task


class HiddenServiceController(Service):
    """Controller for single hidden service instance.

    Will create new ephemeral hidden service
    """
    controller: Controller

    app_port: str
    private_key: str = 'RSA1024'
    private_key_type: str = 'NEW'
    service_id: Optional[str] = None

    _service_id_future: asyncio.Future

    service_created = False

    def __init__(self,
                 app_port: str = '8080',
                 private_key='RSA1024',
                 private_key_type='NEW',
                 stem_host='localhost',
                 stem_port='default',
                 **kwargs):
        self.app_port = app_port
        self.controller = Controller.from_port(stem_host, stem_port)
        self.controller.authenticate()
        self.private_key = private_key
        self.private_key_type = private_key_type
        self._service_id_future = self.loop.create_future()
        super().__init__(**kwargs)

    async def start(self):
        await super().start()

        self.log.info("Creating ephemeral hidden service for %s ...", self.name)
        if self.private_key_type == 'NEW':
            self.log.warning("Starting new hidden service for `%s`", self.name)
        else:
            self.log.debug("Starting with existing private key (%s)", self.private_key_type)

        ports = {
            '80': f'127.0.0.1:{self.app_port}',
        }
        self.log.debug("Hidden service port mapping: %s", ports)
        await asyncio.sleep(10)
        result = self.controller.create_ephemeral_hidden_service(
            ports=ports,
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
        self.log.warning("Hidden service address for `%s` service: %s.onion", self.name, self.service_id)
        self._service_id_future.set_result(result.service_id)

    async def get_service_id(self):
        if self.service_id is None:
            await self._service_id_future
            self.service_id = self._service_id_future.result()
        return self.service_id

    async def stop(self):
        if self.service_created:
            self.log.info("Removing ephemeral hidden service %s...", self.name)
            self.controller.remove_ephemeral_hidden_service(self.service_id)
        self.controller.close()
        await super().stop()
