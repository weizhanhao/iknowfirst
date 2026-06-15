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
            # YouTube 官方原生 RSS:稳定、免 key、免 RSSHub
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch.channel_id}"
        elif ch.handle:
            # 仅有 handle 时退回 RSSHub
            url = f"{base}/youtube/user/{ch.handle}"
        else:
            continue
        feeds.append(Feed("youtube", url, ch.name))
    for acct in cfg.sources.x_accounts:
        feeds.append(Feed("x", f"{base}/twitter/user/{acct}", acct))
    for up in cfg.sources.bilibili_uids:
        if up.uid:
            feeds.append(Feed("bilibili", f"{base}/bilibili/user/video/{up.uid}", up.name))
    for cat in cfg.sources.arxiv_categories:
        # arXiv 官方原生 RSS
        feeds.append(Feed("arxiv", f"http://export.arxiv.org/rss/{cat}", cat))
    if cfg.sources.hf_daily_papers:
        feeds.append(Feed("arxiv", f"{base}/huggingface/daily-papers", "hf-daily"))
    return feeds
