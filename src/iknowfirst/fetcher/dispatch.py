from __future__ import annotations
from iknowfirst.db.models import Item
from iknowfirst.fetcher.base import Fetcher, FetchResult
from iknowfirst.fetcher.arxiv import ArxivFetcher

class FetcherDispatch:
    def __init__(self, youtube: Fetcher | None = None):
        self._youtube = youtube
        self._arxiv = ArxivFetcher()

    def fetch(self, item: Item) -> FetchResult:
        if item.source_type == "youtube":
            if self._youtube is not None:
                return self._youtube.fetch(item)
            fallback = f"{item.title}\n{item.raw_text or ''}".strip()
            return FetchResult(text=fallback, degraded=True, note="youtube fetcher 未注入")
        if item.source_type == "arxiv":
            return self._arxiv.fetch(item)
        # x / bilibili：用标题 + RSS 简介
        text = f"{item.title}\n{item.raw_text or ''}".strip()
        return FetchResult(text=text, degraded=not bool(item.raw_text),
                           note=None if item.raw_text else "仅标题")
