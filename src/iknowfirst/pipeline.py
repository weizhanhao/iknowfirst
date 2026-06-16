from __future__ import annotations
import logging
from iknowfirst.filtering import match_keywords
from iknowfirst.db.models import Item

log = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, repo, keywords: set[str], fetcher, analyzer, notifier,
                 likes_per_hour_provider=None, arxiv_major_threshold: int = 95):
        self._repo = repo
        self._keywords = {k.lower() for k in keywords}
        self._fetcher = fetcher
        self._analyzer = analyzer
        self._notifier = notifier
        # 论文(高产源)只在"超级重磅"分数以上才推,否则解读后丢弃,避免刷屏
        self._arxiv_major_threshold = arxiv_major_threshold
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
            # 论文只在"超级重磅"分以上才推,否则解读后丢弃(不秒推也不进汇总)
            if item.source_type == "arxiv" and res.value_score < self._arxiv_major_threshold:
                self._repo.set_status(item.id, "analyzed")
                return
            self._notifier.handle(title=item.title, url=item.url, author=item.author,
                                  source_type=item.source_type, res=res,
                                  likes_per_hour=lph, degraded=fetched.degraded)
            self._repo.set_status(item.id, "analyzed")
        except Exception:
            log.exception("pipeline failed for item %s", item.external_id)
            self._repo.set_status(item.id, "error")
