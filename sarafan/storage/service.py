from pathlib import Path
from typing import Union

from core_service import Service

from ..magnet import magnet_path


PathLike = Union[str, Path]


class StorageService(Service):
    base_path: Path

    def __init__(self, base_path: PathLike, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path

    def get_absolute_path(self, magnet) -> Path:
        return self.base_path / magnet_path(magnet)
