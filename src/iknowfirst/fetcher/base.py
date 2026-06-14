from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from iknowfirst.db.models import Item

@dataclass
class FetchResult:
    text: str
    degraded: bool = False
    note: str | None = None

class Fetcher(Protocol):
    def fetch(self, item: Item) -> FetchResult: ...
