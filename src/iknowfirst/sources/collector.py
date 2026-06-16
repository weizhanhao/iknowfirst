from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
import feedparser
from iknowfirst.db.models import Item
from iknowfirst.db.repository import ItemRepository
from iknowfirst.sources.feeds import Feed

log = logging.getLogger(__name__)

@dataclass
class ParsedEntry:
    external_id: str
    title: str
    url: str
    author: str | None
    published_at: datetime | None
    summary: str | None = None

def default_parser(feed: Feed) -> list[ParsedEntry]:
    parsed = feedparser.parse(feed.url)
    out: list[ParsedEntry] = []
    for e in parsed.entries:
        ext = getattr(e, "id", None) or getattr(e, "link", None)
        if not ext:
            continue
        published = None
        if getattr(e, "published_parsed", None):
            published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        summary = getattr(e, "summary", None)
        out.append(ParsedEntry(
            external_id=ext, title=getattr(e, "title", ""),
            url=getattr(e, "link", ""), author=getattr(e, "author", None),
            published_at=published, summary=summary))
    return out

class Collector:
    def __init__(self, repo: ItemRepository, parser: Callable[[Feed], list[ParsedEntry]] = default_parser):
        self._repo = repo
        self._parse = parser

    def collect_feed(self, feed: Feed, first_run: bool) -> list[Item]:
        try:
            entries = self._parse(feed)
        except Exception:
            log.exception("feed parse failed: %s", feed.url)
            return []
        ids = [e.external_id for e in entries]
        seen = self._repo.existing_external_ids(ids)
        new_items = []
        for e in entries:
            if e.external_id in seen:
                continue
            status = "seen" if first_run else "new"
            # 用配置里的源名字(频道/账号/类别)作为"来源",比原始 author 更清晰一致
            item = self._repo.add_new(feed.source_type, e.external_id, e.title, e.url,
                                      feed.label, e.published_at, status=status,
                                      raw_text=e.summary)
            if not first_run:
                new_items.append(item)
        return new_items
