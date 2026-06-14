from __future__ import annotations

def match_keywords(text: str, keywords: set[str]) -> list[str]:
    """返回命中的关键词（已小写、去重、排序）。keywords 必须为小写集合。"""
    if not text:
        return []
    low = text.lower()
    return sorted({kw for kw in keywords if kw and kw in low})
