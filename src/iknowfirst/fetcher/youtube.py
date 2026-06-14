from __future__ import annotations
import logging
from typing import Callable
from iknowfirst.db.models import Item
from iknowfirst.fetcher.base import FetchResult

log = logging.getLogger(__name__)

def ytdlp_extract_subtitles(url: str) -> str | None:
    """用 yt-dlp 拉自动字幕，拼成纯文本；无字幕返回 None。
    实现细节：用 writeautomaticsub/writesubtitles，subtitleslangs=[en,zh-Hans,zh]，
    取首个可用语言轨道，下载 json3/vtt 后抽取纯文本拼接返回。"""
    import yt_dlp
    opts = {"skip_download": True, "writeautomaticsub": True, "writesubtitles": True,
            "subtitleslangs": ["en", "zh-Hans", "zh"], "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    subs = info.get("automatic_captions") or info.get("subtitles") or {}
    for lang in ("en", "zh-Hans", "zh"):
        if lang in subs and subs[lang]:
            return _download_caption_text(subs[lang])
    return None

def _download_caption_text(tracks) -> str | None:
    """tracks 为 [{ext,url,...}]；下载 json3/vtt 轨道并抽取文本。
    实现：用 httpx.get(track['url'])，json3 取每个 events[].segs[].utf8 拼接；
    vtt 去时间轴行后拼接。失败返回 None。"""
    import httpx
    track = next((t for t in tracks if t.get("ext") in ("json3", "vtt")), tracks[0])
    try:
        resp = httpx.get(track["url"], timeout=15.0)
        resp.raise_for_status()
    except Exception:
        return None
    if track.get("ext") == "json3":
        import json
        data = json.loads(resp.text)
        parts = [seg.get("utf8", "") for ev in data.get("events", []) for seg in ev.get("segs", [])]
        text = "".join(parts).strip()
        return text or None
    # vtt：丢掉时间轴/序号行
    lines = [ln for ln in resp.text.splitlines()
             if ln and "-->" not in ln and not ln.strip().isdigit() and ln.strip() != "WEBVTT"]
    text = " ".join(lines).strip()
    return text or None

class YoutubeFetcher:
    def __init__(self, extract_subtitles: Callable[[str], str | None] = ytdlp_extract_subtitles):
        self._extract = extract_subtitles

    def fetch(self, item: Item) -> FetchResult:
        try:
            subs = self._extract(item.url)
        except Exception:
            log.exception("subtitle extract failed: %s", item.url)
            subs = None
        if subs:
            return FetchResult(text=subs, degraded=False)
        fallback = f"{item.title}\n{item.raw_text or ''}".strip()
        return FetchResult(text=fallback, degraded=True, note="未取到字幕")
