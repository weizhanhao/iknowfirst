from __future__ import annotations
from datetime import datetime
from sqlalchemy import select, update
from iknowfirst.db.models import Item

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
