from __future__ import annotations
import logging
from iknowfirst.filtering import match_keywords
from iknowfirst.db.models import Item

log = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, repo, keywords: set[str], fetcher, analyzer, notifier,
                 likes_per_hour_provider=None):
        self._repo = repo
        self._keywords = {k.lower() for k in keywords}
        self._fetcher = fetcher
        self._analyzer = analyzer
        self._notifier = notifier
        # 可选：item -> likes/hour 回调（热度追踪结果）；默认 0
        self._lph = likes_per_hour_provider or (lambda item: 0.0)

    def process(self, item: Item) -> None:
        hay = f"{item.title} {item.raw_text or ''}"
        if not match_keywords(hay, self._keywords):
            self._repo.set_status(item.id, "skipped")
            return
        self._repo.set_status(item.id, "matched")
        try:
            fetched = self._fetcher.fetch(item)
            if fetched.text:
                self._repo.set_raw_text(item.id, fetched.text)
            lph = self._lph(item)
            res = self._analyzer.analyze(title=item.title, text=fetched.text, likes_per_hour=lph)
            self._notifier.handle(title=item.title, url=item.url, author=item.author,
                                  source_type=item.source_type, res=res,
                                  likes_per_hour=lph, degraded=fetched.degraded)
            self._repo.set_status(item.id, "analyzed")
        except Exception:
            log.exception("pipeline failed for item %s", item.external_id)
            self._repo.set_status(item.id, "error")
