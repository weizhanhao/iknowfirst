from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey, func, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(16))
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="seen", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    engagement_promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="item")
    samples: Mapped[list["EngagementSample"]] = relationship(back_populates="item")

class EngagementSample(Base):
    __tablename__ = "engagement_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    item: Mapped["Item"] = relationship(back_populates="samples")

class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    highlights: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_score: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(16), default="normal")
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    item: Mapped["Item"] = relationship(back_populates="analyses")

class Push(Base):
    __tablename__ = "pushes"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    tier: Mapped[str] = mapped_column(String(16))
    digest_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
