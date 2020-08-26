import asyncio
import logging
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Type, Union

from core_service import Service, task

from ..ethereum import Contract, EthereumNodeClient
from ..ethereum.block_range import BlockRange
from ..ethereum.contract import BaseContractEvent
from ..logging_helpers import pformat


log = logging.getLogger("sarafan_app")


EventTypeOrList = Union[
    Iterable[Type[BaseContractEvent]],
    Type[BaseContractEvent]
]

SubscriptionsMapping = Dict[Type[BaseContractEvent], List[asyncio.Queue]]


class ContractEventService(Service):

    """Contract event service.

    Listen for specific event types on contract and notify subscribers.

    Service should be started with `start()` and stopped with `stop()`.

    Client should call `subscribe()` before service start. Returned queue
    should be used to consume new events.
    """

    #: Ethereum node client
    client: EthereumNodeClient
    #: Ethereum contract
    contract: Contract
    #: block range to iterate over
    block_range: Optional[BlockRange]
    #: number of seconds to sleep between polling for new block
    block_sleep_interval: float = 30.0
    #: current block number
    current_block_number: Optional[int] = None

    _subscriptions: SubscriptionsMapping

    def __init__(
        self,
        node_client: EthereumNodeClient,
        contract: Contract,
        block_range: Optional[BlockRange] = None,
        block_sleep_interval: float = 10.0,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.client = node_client
        self.contract = contract
        if block_range is None:
            block_range = BlockRange(from_block=0)
        self.block_range = block_range
        self.block_sleep_interval = block_sleep_interval

        self._subscriptions = defaultdict(list)

        # FIXME: should be flushed sometime
        #  used to remove duplicates while loading events, not a good solution
        self._loaded_events = set()

    async def stop(self):
        await self.client.close()
        await super().stop()

    def subscribe(self,
                  event_type: EventTypeOrList,
                  queue: Optional[asyncio.Queue] = None) -> asyncio.Queue:
        """Subscribe to specified contract events.

        :param event_type: contract event type or list of them
        :param queue: optional queue to use instead of creating new one
        :return: queue with contract events
        """
        # issubclass for linter
        if isinstance(event_type, type) and issubclass(event_type, BaseContractEvent):
            event_type = [event_type]
        if queue is None:
            queue = asyncio.Queue()
        for t in event_type:
            self._subscriptions[t].append(queue)
        return queue

    async def notify_subscribers(self, contract_event: BaseContractEvent):
        for queue in self._subscriptions.get(contract_event.__class__, []):
            await queue.put(contract_event)
        listener_count = len(self._subscriptions.get(contract_event.__class__, []))
        if listener_count > 0:
            log.debug(
                "Notify %i subscribers about new event %s",
                listener_count,
                pformat(contract_event),
            )

    @task(periodic=False)
    async def fetch_events_task(self):
        while not self.should_stop:
            await self.fetch_events()
            if self.block_range.reverse:
                log.debug("First block processed, finishing reverse block iteration")
                break
            if self.block_range.to_block is not None:
                log.debug("To block defined and reached, finish forward block iteration")
                break
            # do not process blocks twice, replace block range with shifted to last block
            self.block_range = BlockRange(
                from_block=self.current_block_number or 0,
                to_block=None,
                start_size=self.block_range.step_size,
                max_size=self.block_range.max_size,
                min_size=self.block_range.min_size,
                target_time=self.block_range.target_time,
            )
            log.debug("All available events received, wait for next block")
            await asyncio.sleep(self.block_sleep_interval)

    async def fetch_events(self):
        self.log.debug("Start fetching events")
        last_block_number = await self.client.block_number()
        for from_block, to_block in self.block_range:
            if to_block > last_block_number:
                to_block = last_block_number
            self.log.debug("Requesting events for %i - %i block range",
                           from_block, to_block)
            resp = await self.client.get_logs(self.contract.address, from_block, to_block)
            if self.block_range.reverse:
                resp = reversed(resp)
            for event in resp:
                if event.transaction_hash in self._loaded_events:
                    continue
                self._loaded_events.add(event.transaction_hash)
                contract_event = self.contract.parse(event)
                self._update_current_block(event.block_number)
                self.log.debug("Notify subscribers about new event %s", pformat(contract_event))
                await self.notify_subscribers(contract_event)
            if to_block == last_block_number:
                self._update_current_block(last_block_number)
                self.log.debug("Last known block fetched, finish `fetch_events`")
                break

    def _update_current_block(self, value):
        if self.current_block_number is None:
            self.current_block_number = value

        if self.block_range.reverse:
            self.current_block_number = min(self.current_block_number, max(value, 0))
        else:
            self.current_block_number = max(self.current_block_number, value)
