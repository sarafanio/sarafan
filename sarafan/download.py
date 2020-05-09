from core_service import Service


class DownloadService(Service):
    """Download manager service.

    Handle download queue. New download can be added with `add` method. Content hash (magnet) should
    be provided. Then, `download_task` will
    handle
    """
    pass
