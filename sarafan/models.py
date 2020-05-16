from dataclasses import dataclass
from typing import Optional


@dataclass
class Publication:
    magnet: str
    reply_to: Optional[str]
    source: str
    size: int
    retention: int



@dataclass
class Post:
    magnet: str
    content: str
