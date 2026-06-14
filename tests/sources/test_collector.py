from iknowfirst.sources.collector import Collector, ParsedEntry
from iknowfirst.sources.feeds import Feed


def _entries():
    return [ParsedEntry(external_id="v1", title="GPT-5.5", url="http://y/v1", author="K", published_at=None),
            ParsedEntry(external_id="v2", title="闲聊", url="http://y/v2", author="K", published_at=None)]

def test_first_run_snapshots_without_returning_new(repo):
    feed = Feed("youtube", "http://rss/1", "K")
    c = Collector(repo, parser=lambda f: _entries())
    new_items = c.collect_feed(feed, first_run=True)
    assert new_items == []                         # 首启不产出待处理
    assert repo.existing_external_ids(["v1", "v2"]) == {"v1", "v2"}  # 但已入库

def test_subsequent_run_returns_only_unseen(repo):
    feed = Feed("youtube", "http://rss/1", "K")
    c = Collector(repo, parser=lambda f: _entries())
    c.collect_feed(feed, first_run=True)            # v1,v2 入库
    entries = _entries() + [ParsedEntry(external_id="v3", title="新模型", url="http://y/v3", author="K", published_at=None)]
    c2 = Collector(repo, parser=lambda f: entries)
    new_items = c2.collect_feed(feed, first_run=False)
    assert [i.external_id for i in new_items] == ["v3"]

def test_parser_failure_is_swallowed(repo):
    def boom(_): raise RuntimeError("feed down")
    c = Collector(repo, parser=boom)
    assert c.collect_feed(Feed("youtube", "http://x", "K"), first_run=False) == []


def test_collect_feed_stores_summary_as_raw_text(repo):
    """RSS summary should be captured and stored as raw_text on the item."""
    entry_with_summary = ParsedEntry(
        external_id="s1", title="Paper Title", url="http://y/s1",
        author="A", published_at=None, summary="This is the abstract text.")
    feed = Feed("arxiv", "http://rss/arxiv", "arxiv")
    c = Collector(repo, parser=lambda f: [entry_with_summary])
    new_items = c.collect_feed(feed, first_run=False)
    assert len(new_items) == 1
    # Fetch from repo to verify raw_text was persisted
    stored = repo.items_by_status("new")
    assert len(stored) == 1
    assert stored[0].raw_text == "This is the abstract text."
