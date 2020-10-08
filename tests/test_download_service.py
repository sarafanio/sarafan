import asyncio

import pytest

from sarafan.download import DownloadService
from sarafan.storage import StorageService


@pytest.mark.asyncio
async def test_download_simple():
    storage = StorageService(base_path='./content_tmp')
    service = DownloadService(storage=storage)

    await service.start()
    await asyncio.sleep(0)
    await service.stop()
