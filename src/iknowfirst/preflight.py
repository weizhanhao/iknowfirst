from __future__ import annotations
import os
import sys
import logging
from dataclasses import dataclass
from typing import Callable

@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""

def run_checks(checks: list[Callable[[], Check]]) -> list[Check]:
    results: list[Check] = []
    for c in checks:
        try:
            results.append(c())
        except Exception as e:
            results.append(Check(getattr(c, "__name__", "check"), False, str(e)[:200]))
    return results

def all_ok(results: list[Check]) -> bool:
    return all(r.ok for r in results)

def format_report(results: list[Check]) -> str:
    lines = []
    for r in results:
        mark = "✅" if r.ok else "❌"
        lines.append(f"{mark} {r.name}" + (f" — {r.detail}" if r.detail else ""))
    return "\n".join(lines)

# ---- 具体检查(读 config/env/网络;这些不单测,集成手测) ----
def _check_config():
    from iknowfirst.config import load_config
    path = os.environ.get("CONFIG_PATH", "config.yaml")
    cfg = load_config(path)
    return Check("config 加载", True, f"{len(cfg.sources.youtube_channels)} youtube / {len(cfg.all_keywords())} 关键词")

def _check_env():
    missing = [v for v in ("DATABASE_URL", "AGNES_API_KEY", "WECOM_WEBHOOK_URL") if not os.environ.get(v)]
    if missing:
        return Check("必需环境变量", False, "缺少: " + ", ".join(missing))
    return Check("必需环境变量", True, "DATABASE_URL / AGNES_API_KEY / WECOM_WEBHOOK_URL 已设置")

def _check_agnes():
    from openai import OpenAI
    base = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
    c = OpenAI(base_url=base, api_key=os.environ["AGNES_API_KEY"], timeout=20.0)
    r = c.chat.completions.create(model=os.environ.get("AGNES_MODEL", "agnes-2.0-flash"),
                                  messages=[{"role": "user", "content": "ok"}], temperature=0)
    return Check("Agnes 可达", True, f"模型应答 {len((r.choices[0].message.content or ''))} 字")

def _check_youtube():
    import httpx
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return Check("YouTube key(可选)", True, "未设置(热度采样将关闭)")
    r = httpx.get("https://www.googleapis.com/youtube/v3/videos",
                  params={"part": "statistics", "id": "dQw4w9WgXcQ", "key": key}, timeout=20.0)
    r.raise_for_status()
    if not r.json().get("items"):
        return Check("YouTube key", False, "请求成功但无数据")
    return Check("YouTube key", True, "可读公开视频统计")

def _check_rsshub():
    import httpx
    from iknowfirst.config import load_config
    from iknowfirst.sources.feeds import build_feeds
    cfg = load_config(os.environ.get("CONFIG_PATH", "config.yaml"))
    feeds = build_feeds(cfg)
    if not feeds:
        return Check("RSSHub feed", False, "未构建出任何 feed")
    import feedparser
    # 取第一个 youtube feed 试抓
    f = next((x for x in feeds if x.source_type == "youtube"), feeds[0])
    parsed = feedparser.parse(f.url)
    n = len(parsed.entries)
    return Check("RSSHub 首个 feed", n > 0, f"{f.label}: {n} 条" if n > 0 else f"{f.label}: 0 条(检查 RSSHub 是否在 {cfg.rsshub_base_url})")

def main() -> int:
    logging.disable(logging.CRITICAL)
    checks = [_check_config, _check_env, _check_agnes, _check_youtube, _check_rsshub]
    results = run_checks(checks)
    print(format_report(results))
    ok = all_ok(results)
    print("\n" + ("✅ 预检通过,可以启动。" if ok else "❌ 预检有失败项,修复后再启动。"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
