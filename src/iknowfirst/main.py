from __future__ import annotations
import logging, os
from apscheduler.schedulers.blocking import BlockingScheduler
from iknowfirst.config import load_config
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

log = logging.getLogger(__name__)

def build_llm(cfg):
    primary = OpenAICompatibleLLM(cfg.llm.provider, cfg.llm.base_url,
                                  cfg.llm.resolved_api_key, cfg.llm.model)
    return FallbackLLM(primary, fallback=None)  # v1 先不接备用实例；接法见 README

def main():
    setup_logging()
    cfg = load_config(os.environ.get("CONFIG_PATH", "config.yaml"))
    sf = make_session_factory(os.environ["DATABASE_URL"])
    repo = ItemRepository(sf)
    feeds = build_feeds(cfg)
    collector = Collector(repo)
    fetcher = FetcherDispatch(youtube=YoutubeFetcher())
    llm = build_llm(cfg)
    analyzer = Analyzer(llm, cfg.push.major_value_threshold)
    wecom = WecomClient(cfg.push.webhook_url)
    notifier = Notifier(wecom)
    trendscout = TrendScout(llm, wecom, cfg.trendscout.mode)
    pipeline = Pipeline(repo, cfg.all_keywords(), fetcher, analyzer, notifier)

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
    log.info("iknowfirst started: %d feeds, poll every %dmin", len(feeds), cfg.poll_interval_minutes)
    sched.start()

if __name__ == "__main__":
    main()
