from __future__ import annotations
import json
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是 AI 领域资深编辑。读用户给的视频字幕/论文摘要/推文，"
    "输出严格 JSON：{\"summary\":一句话中文总结, \"highlights\":[2-4个亮点], "
    "\"recommendation\":要不要看/适合谁, \"value_score\":0-100整数价值分}。只输出 JSON。"
)

@dataclass(frozen=True)
class AnalysisResult:
    summary: str
    highlights: list[str]
    recommendation: str
    value_score: int
    tier: str

def decide_tier(value_score: int, likes_per_hour: float, threshold: int,
                velocity_major: float = 2000.0) -> str:
    if value_score >= threshold or likes_per_hour >= velocity_major:
        return "major"
    return "normal"

class Analyzer:
    def __init__(self, llm, major_value_threshold: int = 80, velocity_major: float = 2000.0):
        self._llm = llm
        self._threshold = major_value_threshold
        self._velocity_major = velocity_major

    def analyze(self, title: str, text: str, likes_per_hour: float = 0.0) -> AnalysisResult:
        user = f"标题：{title}\n\n正文：\n{text[:6000]}"
        raw = self._llm.complete(SYSTEM_PROMPT, user)
        try:
            data = json.loads(raw)
            summary = str(data["summary"])
            highlights = [str(h) for h in data.get("highlights", [])]
            recommendation = str(data.get("recommendation", ""))
            score = int(data.get("value_score", 0))
        except Exception:
            log.warning("analyzer got non-JSON payload; using fallback")
            summary = raw.strip()[:200] or title
            highlights, recommendation, score = [], "", 0
        tier = decide_tier(score, likes_per_hour, self._threshold, self._velocity_major)
        return AnalysisResult(summary, highlights, recommendation, score, tier)
