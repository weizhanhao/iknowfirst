from __future__ import annotations
from datetime import datetime

def likes_per_hour(samples: list[tuple[datetime, int]]) -> float:
    """据时间序列样本计算点赞增速（每小时）。样本不足返回 0。"""
    if len(samples) < 2:
        return 0.0
    samples = sorted(samples, key=lambda s: s[0])
    (t_first, v_first), (t_last, v_last) = samples[0], samples[-1]
    hours = (t_last - t_first).total_seconds() / 3600.0
    if hours <= 0:
        return 0.0
    return round((v_last - v_first) / hours, 2)
