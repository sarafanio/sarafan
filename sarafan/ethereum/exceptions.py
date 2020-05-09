class EthereumNodeException(Exception):
    """General ethereum node exception.
    """

    pass


class FilterNotFound(EthereumNodeException):
    """Filter not found node exception.

    Filter will be recreated next time.
    """

    pass


EXCEPTIONS_MAP = {
    "Filter not found": FilterNotFound,
}
