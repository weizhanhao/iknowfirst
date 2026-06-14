from __future__ import annotations
from iknowfirst.db.models import Item
from iknowfirst.fetcher.base import FetchResult

class ArxivFetcher:
    def fetch(self, item: Item) -> FetchResult:
        text = (item.raw_text or item.title).strip()
        return FetchResult(text=text, degraded=not bool(item.raw_text),
                           note=None if item.raw_text else "仅标题")
