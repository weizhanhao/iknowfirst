def test_existing_ids_and_add_new(repo):
    assert repo.existing_external_ids(["a", "b"]) == set()
    repo.add_new("youtube", "a", "标题A", "http://y/a", author=None, published_at=None, status="seen")
    assert repo.existing_external_ids(["a", "b"]) == {"a"}

def test_set_status_and_fetch_matched(repo):
    item = repo.add_new("youtube", "c", "标题C", "http://y/c", author=None, published_at=None, status="matched")
    matched = repo.items_by_status("matched")
    assert [i.external_id for i in matched] == ["c"]
    repo.set_status(item.id, "analyzed")
    assert repo.items_by_status("matched") == []

def test_set_raw_text(repo):
    item = repo.add_new("youtube", "d", "标题D", "http://y/d", author=None, published_at=None, status="matched")
    repo.set_raw_text(item.id, "字幕正文")
    got = repo.items_by_status("matched")[0]
    assert got.raw_text == "字幕正文"
