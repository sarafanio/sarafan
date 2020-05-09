import logging
import math

log = logging.getLogger(__name__)


class BlockRange:
    """Block range iterator.

    Generate a pairs of (from_block, to_block).

    `retry` method can be used to drastically decrease range on next iteration

    `record_time` should be used to record response time and align range size to achieve
        `target_time` the next time
    """

    def __init__(
        self,
        from_block: int = None,
        to_block: int = None,
        start_size: int = 100000,
        max_size: int = 1000000,
        min_size: int = 1,
        reverse: int = False,
        target_time: float = 10.0,
    ):
        assert (
            from_block is not None or to_block is not None
        ), "One of `from_block` or `to_block` should be provided"
        if from_block is None:
            from_block = 0
        self.from_block = from_block
        self.cursor = from_block
        self.to_block = to_block
        self.step_size = start_size
        self.max_size = max_size
        self.min_size = min_size
        self.reverse = reverse
        self.target_time = target_time

    @property
    def step(self):
        s = self.step_size - 1
        return -s if self.reverse else s

    def __iter__(self):
        if self.reverse:
            _to = self.to_block
            _from = _to + self.step
            if _from < self.from_block:
                _from = self.from_block
        else:
            _from = self.from_block or 0
            _to = _from + self.step
            if self.to_block and _to > self.to_block:
                _to = self.to_block

        self._to = _to
        self._from = _from

        while True:
            yield self._from, self._to
            if self.reverse:
                self._to = self._from - 1
                self._from = self._to + self.step
            else:
                self._from = self._to + 1
                self._to = self._from + self.step
            if self._to < 0:
                log.debug("End of block range")
                return

    def retry(self):
        """Retry last interval with decreased step size.

        Step size will be decreased by 2 but will be not less than minimal step size.
        """
        if self.reverse:
            self._to -= self.step - 1
            self._from -= self.step - 1
        else:
            self._to -= self.step + 1
            self._from -= self.step + 1

        self.step_size = self.step_size // 2
        if self.step_size < self.min_size:
            self.step_size = self.min_size

    def record_time(self, t: float):
        """Record last interval execution time and adjust step size according it.

        TODO: moving average should be used

        :param t: number of seconds last interval executed
        :return: new step size
        """
        self.step_size = min(
            max(
                math.ceil(self.step_size * min(max(self.target_time / t, 0.5), 2)),
                self.min_size,
            ),
            self.max_size,
        )
        return self.step_size
