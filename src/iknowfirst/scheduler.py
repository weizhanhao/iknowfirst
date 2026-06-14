from __future__ import annotations
import logging
from iknowfirst.sources.collector import Collector
from iknowfirst.sources.feeds import Feed
from iknowfirst.pipeline import Pipeline

log = logging.getLogger(__name__)

def run_poll_cycle(collector: Collector, feeds: list[Feed], pipeline: Pipeline,
                   first_run: bool) -> None:
    for feed in feeds:
        new_items = collector.collect_feed(feed, first_run=first_run)
        for item in new_items:
            pipeline.process(item)
