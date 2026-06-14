from __future__ import annotations
import json
import logging

log = logging.getLogger(__name__)

SYSTEM = (
    "你是 AI 趋势分析师。给你一批近期内容标题，找出反复出现、"
    "代表 AI 新模型/新术语/新热点的词。输出严格 JSON：{\"new_keywords\":[...]}。只输出 JSON。"
)

class TrendScout:
    def __init__(self, llm, wecom, mode: str = "suggest"):
        self._llm = llm
        self._wecom = wecom
        self._mode = mode

    def run(self, titles: list[str], current_keywords: set[str]) -> list[str]:
        if not titles:
            return []
        user = "标题列表：\n" + "\n".join(f"- {t}" for t in titles[:300])
        try:
            data = json.loads(self._llm.complete(SYSTEM, user))
            candidates = [str(k).strip() for k in data.get("new_keywords", []) if str(k).strip()]
        except Exception:
            log.warning("trendscout got non-JSON; skipping this run")
            return []
        current_low = {k.lower() for k in current_keywords}
        fresh = [k for k in candidates if k.lower() not in current_low]
        if not fresh:
            return []
        if self._mode == "suggest":
            body = "📈 **本周 AI 新热词建议**\n\n" + "、".join(fresh) + "\n\n回复要加入关键词库的词。"
            try:
                self._wecom.send_markdown(body)
            except Exception:
                log.exception("trendscout wecom send failed")
        return fresh
