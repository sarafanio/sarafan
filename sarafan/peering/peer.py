from dataclasses import dataclass
from typing import Optional


@dataclass
class Peer:
    service_id: str
    content_service_id: Optional[str] = None
    version: Optional[str] = None
    rating: float = .0
    address: Optional[str] = None

    def __hash__(self):
        return hash(self.service_id)
