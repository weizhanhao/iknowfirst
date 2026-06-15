from __future__ import annotations
from datetime import datetime
from sqlalchemy import select, update, asc
from iknowfirst.db.models import Item, EngagementSample

DEFAULT_BATCH_LIMIT = 500

class ItemRepository:
    """封装 items 表的数据访问，业务层不直接写 SQL（便于迁移）。"""
    def __init__(self, session_factory):
        self._sf = session_factory

    def existing_external_ids(self, external_ids: list[str]) -> set[str]:
        if not external_ids:
            return set()
        with self._sf() as s:
            rows = s.execute(
                select(Item.external_id).where(Item.external_id.in_(external_ids))
            ).scalars().all()
        return set(rows)

    def add_new(self, source_type: str, external_id: str, title: str, url: str,
                author: str | None, published_at: datetime | None, status: str,
                raw_text: str | None = None) -> Item:
        # 外部数据边界防御:截断超长字段以适配列宽(如 arXiv 多作者列表)
        source_type = (source_type or "")[:16]
        external_id = (external_id or "")[:255]
        title = (title or "")[:512]
        url = (url or "")[:1024]
        author = author[:255] if author else None
        with self._sf() as s:
            item = Item(source_type=source_type, external_id=external_id, title=title,
                        url=url, author=author, published_at=published_at, status=status,
                        raw_text=raw_text)
            s.add(item); s.commit(); s.refresh(item)
            s.expunge(item)
            return item

    def items_by_status(self, status: str, limit: int = DEFAULT_BATCH_LIMIT) -> list[Item]:
        with self._sf() as s:
            rows = s.execute(select(Item).where(Item.status == status).limit(limit)).scalars().all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def set_status(self, item_id: int, status: str) -> None:
        with self._sf() as s:
            s.execute(update(Item).where(Item.id == item_id).values(status=status))
            s.commit()

    def set_raw_text(self, item_id: int, raw_text: str) -> None:
        with self._sf() as s:
            s.execute(update(Item).where(Item.id == item_id).values(raw_text=raw_text))
            s.commit()

    def youtube_tracked_items(self, created_after: datetime, limit: int = DEFAULT_BATCH_LIMIT) -> list[Item]:
        with self._sf() as s:
            rows = s.execute(
                select(Item).where(
                    Item.source_type == "youtube",
                    Item.created_at >= created_after,
                    Item.status.notin_(["seen", "skipped"]),
                ).limit(limit)
            ).scalars().all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def add_engagement_sample(self, item_id: int, views: int, likes: int, comments: int,
                              sampled_at: datetime | None = None) -> None:
        with self._sf() as s:
            kw = {"item_id": item_id, "views": views, "likes": likes, "comments": comments}
            if sampled_at is not None:
                kw["sampled_at"] = sampled_at
            s.add(EngagementSample(**kw)); s.commit()

    def likes_samples_for(self, item_id: int) -> list[tuple[datetime, int]]:
        with self._sf() as s:
            rows = s.execute(
                select(EngagementSample.sampled_at, EngagementSample.likes)
                .where(EngagementSample.item_id == item_id)
                .order_by(asc(EngagementSample.sampled_at))
            ).all()
            return [(r[0], r[1]) for r in rows]

    def mark_engagement_promoted(self, item_id: int) -> None:
        with self._sf() as s:
            s.execute(update(Item).where(Item.id == item_id).values(engagement_promoted=True))
            s.commit()
