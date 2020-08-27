import os
import shutil
from pathlib import Path
from typing import Union

from aiohttp import StreamReader
from Cryptodome.Hash import keccak
from Cryptodome.Random import random

from core_service import Service

from ..magnet import magnet_path
from ..peering.client import InvalidChecksum

PathLike = Union[str, Path]


class StorageService(Service):
    base_path: Path

    def __init__(self, base_path: PathLike, **kwargs):
        super().__init__(**kwargs)
        self.base_path = Path(base_path)

    async def store(self, magnet: str, content: StreamReader, chunk_size=1024):
        """Check and store content file.

        :param magnet:
        :param content:
        :param chunk_size:
        :return:
        """
        to_path = self.get_absolute_path(magnet)
        # content_path = Path(to_path) / magnet_path(magnet)
        tmp_content_path = ''.join([str(to_path), 'tmp.%s' % random.randint(10000, 99999)])
        check = keccak.new(digest_bytes=32)

        try:
            with open(tmp_content_path, 'wb') as fd:
                async for chunk, _ in content.iter_chunks():
                    fd.write(chunk)
                    check.update(data=chunk)

            checksum = check.hexdigest()
            if checksum != magnet:
                self.log.error("Downloaded content file %s checksum %s didn't match", magnet, checksum)
                raise InvalidChecksum(magnet, checksum)
            shutil.move(tmp_content_path, to_path)
        finally:
            os.unlink(tmp_content_path)

    def get_absolute_path(self, magnet) -> Path:
        return self.base_path / magnet_path(magnet)

    def get_unpack_path(self, magnet: str):
        """Get local path for unpacked publication content.
        """
        return self.base_path / 'unpacked' / magnet_path(magnet)
