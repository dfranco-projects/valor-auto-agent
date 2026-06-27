from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Search(Base):
    __tablename__ = "search"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    filters_json: Mapped[dict] = mapped_column(JSON)
    sources: Mapped[str] = mapped_column(String(64))
    scrape_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scrape_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")

    listings: Mapped[list[Listing]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class Listing(Base):
    __tablename__ = "listing"
    __table_args__ = (UniqueConstraint("search_id", "source", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("search.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(512))
    price_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transmission: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url: Mapped[str] = mapped_column(String(1024))
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)

    search: Mapped[Search] = relationship(back_populates="listings")
    rating: Mapped[Rating | None] = relationship(
        back_populates="listing", uselist=False, cascade="all, delete-orphan"
    )


class Rating(Base):
    __tablename__ = "rating"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listing.id", ondelete="CASCADE"), unique=True
    )
    score: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(String(2048))
    model: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    listing: Mapped[Listing] = relationship(back_populates="rating")


class Evaluation(Base):
    # a shopper decision on a car, keyed by (source, external_id) so it follows
    # the car across re-searches rather than a single listing row
    __tablename__ = "evaluation"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(String(4096), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class UiPref(Base):
    # single-row (id=1) ui state so the active chat thread + rater model survive reloads
    __tablename__ = "ui_pref"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rater_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class UserMemory(Base):
    # long-term per-user search preferences (last-value-wins per filter field), used to
    # pre-fill the filter form for gaps the natural-language query didn't specify
    __tablename__ = "user_memory"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    prefs_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class ChatSession(Base):
    # one row per chat thread, titled by its first user message, for the sidebar history
    __tablename__ = "chat_session"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
