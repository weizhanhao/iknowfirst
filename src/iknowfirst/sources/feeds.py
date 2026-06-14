from __future__ import annotations
from dataclasses import dataclass
from iknowfirst.config import Config

@dataclass(frozen=True)
class Feed:
    source_type: str
    url: str
    label: str

def build_feeds(cfg: Config) -> list[Feed]:
    base = cfg.rsshub_base_url.rstrip("/")
    feeds: list[Feed] = []
    for ch in cfg.sources.youtube_channels:
        if ch.channel_id:
            path = f"/youtube/channel/{ch.channel_id}"
        elif ch.handle:
            path = f"/youtube/user/{ch.handle}"
        else:
            continue
        feeds.append(Feed("youtube", base + path, ch.name))
    for acct in cfg.sources.x_accounts:
        feeds.append(Feed("x", f"{base}/twitter/user/{acct}", acct))
    for up in cfg.sources.bilibili_uids:
        if up.uid:
            feeds.append(Feed("bilibili", f"{base}/bilibili/user/video/{up.uid}", up.name))
    for cat in cfg.sources.arxiv_categories:
        feeds.append(Feed("arxiv", f"{base}/arxiv/{cat}", cat))
    if cfg.sources.hf_daily_papers:
        feeds.append(Feed("arxiv", f"{base}/huggingface/daily-papers", "hf-daily"))
    return feeds
