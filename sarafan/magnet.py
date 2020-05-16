"""
magnet utils
"""
def is_magnet(magnet: str):
    """Check if provided string is a magnet.

    >>> is_magnet('13600b294191fc92924bb3ce4b969c1e7e2bab8f4c93c3fc6d0a51733df3c060')
    True
    >>> is_magnet('123')
    False
    >>> is_magnet(b'123')
    False
    >>> is_magnet('x3600b294191fc92924bb3ce4b969c1e7e2bab8f4c93c3fc6d0a51733df3c060')
    False
    """
    if not isinstance(magnet, str):
        return False
    if len(magnet) != 64:
        return False
    try:
        bytes.fromhex(magnet)
    except ValueError:
        return False
    return True


def magnet_path(magnet: str) -> str:
    """Convert magnet to path to a file in storage.

    For example:

    >>> magnet_path('13600b294191fc92924bb3ce4b969c1e7e2bab8f4c93c3fc6d0a51733df3c060')
    '13600b294191fc92/924bb3ce4b969c1e/7e2bab8f4c93c3fc/6d0a51733df3c060'
    """
    assert is_magnet(magnet), "%s is not a magnet" % magnet
    return '/'.join([
        magnet[i * 16:i * 16 + 16]
        for i in range(4)
    ])
