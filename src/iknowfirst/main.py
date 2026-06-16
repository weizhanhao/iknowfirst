from __future__ import annotations
import logging, os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from iknowfirst.config import load_config, Config
from iknowfirst.logging_setup import setup_logging
from iknowfirst.db.session import make_session_factory
from iknowfirst.db.repository import ItemRepository
from iknowfirst.sources.feeds import build_feeds
from iknowfirst.sources.collector import Collector
from iknowfirst.fetcher.dispatch import FetcherDispatch
from iknowfirst.fetcher.youtube import YoutubeFetcher
from iknowfirst.llm.openai_compatible import OpenAICompatibleLLM
from iknowfirst.llm.factory import FallbackLLM
from iknowfirst.analyzer import Analyzer
from iknowfirst.notify.wecom import WecomClient
from iknowfirst.notify.notifier import Notifier
from iknowfirst.trendscout import TrendScout
from iknowfirst.pipeline import Pipeline
from iknowfirst.scheduler import run_poll_cycle
from iknowfirst.engagement.youtube_api import fetch_stats
from iknowfirst.engagement.sampler import EngagementSampler

log = logging.getLogger(__name__)

def build_llm(cfg: Config) -> FallbackLLM:
    primary = OpenAICompatibleLLM(cfg.llm.provider, cfg.llm.base_url,
                                  cfg.llm.resolved_api_key, cfg.llm.model)
    fb = None
    if cfg.llm.fallback_base_url and cfg.llm.fallback_model and cfg.llm.fallback_api_key_env:
        fb_key = os.environ.get(cfg.llm.fallback_api_key_env)
        if fb_key:
            fb = OpenAICompatibleLLM("fallback", cfg.llm.fallback_base_url, fb_key, cfg.llm.fallback_model)
    return FallbackLLM(primary, fb)

def main():
    setup_logging()
    cfg = load_config(os.environ.get("CONFIG_PATH", "config.yaml"))
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("missing env var DATABASE_URL")
    sf = make_session_factory(db_url)
    repo = ItemRepository(sf)
    feeds = build_feeds(cfg)
    collector = Collector(repo)
    fetcher = FetcherDispatch(youtube=YoutubeFetcher())
    llm = build_llm(cfg)
    analyzer = Analyzer(llm, cfg.push.major_value_threshold, cfg.push.velocity_major_threshold)
    wecom = WecomClient(cfg.push.webhook_url)
    notifier = Notifier(wecom)
    trendscout = TrendScout(llm, wecom, cfg.trendscout.mode)
    pipeline = Pipeline(repo, cfg.all_keywords(), fetcher, analyzer, notifier,
                        arxiv_major_threshold=cfg.push.arxiv_major_threshold)

    # 启动即做一次首启快照（不补推历史）
    run_poll_cycle(collector, feeds, pipeline, first_run=True)

    sched = BlockingScheduler(timezone="Asia/Shanghai")
    sched.add_job(lambda: run_poll_cycle(collector, feeds, pipeline, first_run=False),
                  "interval", minutes=cfg.poll_interval_minutes)
    for hhmm in cfg.push.digest_times:
        h, m = hhmm.split(":")
        sched.add_job(notifier.flush_digest, "cron", hour=int(h), minute=int(m))
    if cfg.trendscout.enabled:
        th, tm = cfg.trendscout.run_time.split(":")
        sched.add_job(
            lambda: trendscout.run(
                titles=[i.title for i in repo.items_by_status("skipped")],
                current_keywords=cfg.all_keywords()),
            "cron", hour=int(th), minute=int(tm))
    yt_key = os.environ.get("YOUTUBE_API_KEY")
    if cfg.engagement.enabled and yt_key:
        sampler = EngagementSampler(
            repo, fetch=lambda vid: fetch_stats(vid, yt_key), notifier=notifier,
            velocity_major_threshold=cfg.push.velocity_major_threshold,
            track_window_hours=cfg.engagement.track_window_hours)
        sched.add_job(lambda: sampler.run_once(datetime.now()),
                      "interval", minutes=cfg.engagement.sample_interval_minutes,
                      max_instances=1, misfire_grace_time=30)
        log.info("engagement sampler registered: every %dmin", cfg.engagement.sample_interval_minutes)
    log.info("iknowfirst started: %d feeds, poll every %dmin", len(feeds), cfg.poll_interval_minutes)
    sched.start()

if __name__ == "__main__":
    main()
