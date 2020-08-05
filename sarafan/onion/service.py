import socket
from typing import Iterable, Tuple

from stem.control import Controller




class OnionService(Service):
    """Service managing group of hidden (onion) services.
    """
    controller: Controller

    # TODO: allow configuration for usage outside docker
    #: list of (service name, target host/port)
    services: Iterable[Tuple[str, str]] = (
        ('content', 'nginx:80'),
        ('contract', '%s:8080' % socket.gethostname()),
    )
    content: OnionServiceController
    contract: OnionServiceController

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.controller = Controller.from_port(socket.gethostbyname('proxy'))
        self.controller.authenticate()

        for name, target in self.services:
            service = OnionServiceController(
                name=name,
                ports={'80': target},
                controller=self.controller,
                loop=self.loop
            )
            setattr(self, name, service)

    def on_init_dependencies(self):
        return [getattr(self, name) for name, _ in self.services]

    async def stop(self):
        await super().stop()
        if self.controller:
            self.controller.close()
