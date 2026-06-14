from __future__ import annotations
import re
import httpx

_API = "https://www.googleapis.com/youtube/v3/videos"

def extract_video_id(item) -> str | None:
    ext = item.external_id or ""
    if ext.startswith("yt:video:"):
        return ext.split("yt:video:", 1)[1]
    for pat in (r"[?&]v=([A-Za-z0-9_-]{11})", r"youtu\.be/([A-Za-z0-9_-]{11})"):
        m = re.search(pat, item.url or "")
        if m:
            return m.group(1)
    return None

def fetch_stats(video_id: str, api_key: str, timeout: float = 20.0) -> tuple[int, int, int]:
    resp = httpx.get(_API, params={"part": "statistics", "id": video_id, "key": api_key}, timeout=timeout)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise RuntimeError(f"no stats for video {video_id}")
    s = items[0]["statistics"]
    return (int(s.get("viewCount", 0)), int(s.get("likeCount", 0)), int(s.get("commentCount", 0)))
