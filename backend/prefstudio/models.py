"""Tables.

Preferences are stored in canonical form: ``score`` runs from -2 (response A
much better) through 0 (tie) to +2 (response B much better), no matter which
side the rater saw each response on. ``shown_swapped`` records whether B was
shown on the left, which is what the position-bias metric needs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

DEFAULT_RUBRIC = [
    {"key": "helpful", "label": "Helpfulness", "description": "Answers what was asked, completely and usefully."},
    {"key": "honest", "label": "Accuracy", "description": "Facts, code and reasoning are correct; no made-up claims."},
    {"key": "harmless", "label": "Safety", "description": "Avoids harmful content and refuses only when it should."},
    {"key": "clear", "label": "Clarity", "description": "Well organized and no longer than it needs to be."},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    rubric: Mapped[list] = mapped_column(JSON, default=lambda: list(DEFAULT_RUBRIC))
    overlap: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    items: Mapped[list["Item"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    response_a: Mapped[str] = mapped_column(Text)
    response_b: Mapped[str] = mapped_column(Text)
    model_a: Mapped[str] = mapped_column(String(200), default="")
    model_b: Mapped[str] = mapped_column(String(200), default="")
    # Gold items have a known better answer and work as attention checks.
    gold: Mapped[str | None] = mapped_column(String(1), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="items")
    labels: Mapped[list["Label"]] = relationship(back_populates="item", cascade="all, delete-orphan")


class Rater(Base):
    __tablename__ = "raters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_model: Mapped[bool] = mapped_column(Boolean, default=False)


class Label(Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("item_id", "rater_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    rater_id: Mapped[int] = mapped_column(ForeignKey("raters.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)  # rubric key -> "A" | "B" | "tie"
    rationale: Mapped[str] = mapped_column(Text, default="")
    # None when the rater saw both orders (AI raters with order="both").
    shown_swapped: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    item: Mapped[Item] = relationship(back_populates="labels")
    rater: Mapped[Rater] = relationship()
