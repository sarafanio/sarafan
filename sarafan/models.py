from dataclasses import dataclass
from typing import Optional


@dataclass
class Publication:
    magnet: str
    reply_to: Optional[str]
    source: str
    size: int
    retention: int

    # def __init__(self, magnet, reply_to, source, size, retention):
    #     self.magnet = magnet


@dataclass
class Post:
    magnet: str
    content: str
