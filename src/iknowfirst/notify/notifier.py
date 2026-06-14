from __future__ import annotations
import logging
from iknowfirst.analyzer import AnalysisResult

log = logging.getLogger(__name__)

_SOURCE_LABEL = {"youtube": "YouTube", "x": "X", "bilibili": "B站", "arxiv": "论文"}

def format_card(title: str, url: str, author: str | None, source_type: str,
                res: AnalysisResult, likes_per_hour: float, degraded: bool) -> str:
    label = _SOURCE_LABEL.get(source_type, source_type)
    lines = [f"### {title}",
             f"> {label}" + (f" · {author}" if author else ""),
             f"**摘要**：{res.summary}"]
    if res.highlights:
        lines.append("**亮点**：" + "；".join(res.highlights))
    if res.recommendation:
        lines.append(f"**要不要看**：{res.recommendation}")
    if likes_per_hour and likes_per_hour > 0:
        lines.append(f"**热度**：约 +{int(likes_per_hour)} 赞/小时")
    if degraded:
        lines.append("⚠️ 未取到字幕，基于标题/简介解读")
    lines.append(f"[原文链接]({url})")
    return "\n".join(lines)

class Notifier:
    def __init__(self, wecom):
        self._wecom = wecom
        self._digest: list[str] = []

    def _safe_send(self, content: str) -> None:
        try:
            self._wecom.send_markdown(content)
        except Exception:
            log.exception("wecom send failed")

    def handle(self, title, url, author, source_type, res: AnalysisResult,
               likes_per_hour: float, degraded: bool) -> None:
        card = format_card(title, url, author, source_type, res, likes_per_hour, degraded)
        if res.tier == "major":
            self._safe_send("📡 **重磅 AI 动态**\n\n" + card)
        else:
            self._digest.append(card)

    def digest_queue_size(self) -> int:
        return len(self._digest)

    def flush_digest(self) -> None:
        if not self._digest:
            return
        body = "📰 **AI 动态汇总**\n\n" + "\n\n---\n\n".join(self._digest)
        self._safe_send(body)
        self._digest.clear()
