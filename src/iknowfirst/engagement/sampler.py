from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Callable
from iknowfirst.engagement.youtube_api import extract_video_id
from iknowfirst.engagement.tracker import likes_per_hour

log = logging.getLogger(__name__)

class EngagementSampler:
    """周期性采样 YouTube 热度;增速飙升时补推一条重磅(去重)。"""
    def __init__(self, repo, fetch: Callable[[str], tuple[int, int, int]], notifier,
                 velocity_major_threshold: float, track_window_hours: int):
        self._repo = repo
        self._fetch = fetch
        self._notifier = notifier
        self._threshold = velocity_major_threshold
        self._window = track_window_hours

    def run_once(self, now: datetime) -> None:
        cutoff = now - timedelta(hours=self._window)
        for item in self._repo.youtube_tracked_items(cutoff):
            vid = extract_video_id(item)
            if not vid:
                continue
            try:
                views, likes, comments = self._fetch(vid)
            except Exception:
                log.exception("youtube stats fetch failed: %s", item.external_id)
                continue
            self._repo.add_engagement_sample(item.id, views, likes, comments, sampled_at=now)
            lph = likes_per_hour(self._repo.likes_samples_for(item.id))
            if lph >= self._threshold and not item.engagement_promoted:
                self._notifier.push_spike(item.title, item.url, item.author, "youtube", lph)
                self._repo.mark_engagement_promoted(item.id)
                log.info("engagement spike promoted: %s (%.0f likes/h)", item.external_id, lph)
