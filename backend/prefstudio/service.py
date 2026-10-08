"""Database operations shared by the web API and the CLI."""

from __future__ import annotations

import random

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .analysis import ExportOptions, ItemRec, LabelRec, ProjectStats, compute_stats, dpo_pairs
from .models import DEFAULT_RUBRIC, Item, Label, Project, Rater


class NotFound(LookupError):
    pass


class AlreadyLabeled(ValueError):
    pass


def create_project(s: Session, name: str, description: str = "", rubric: list | None = None, overlap: int = 3) -> Project:
    p = Project(name=name, description=description, rubric=rubric or list(DEFAULT_RUBRIC), overlap=overlap)
    s.add(p)
    s.commit()
    return p


def get_project(s: Session, project_id: int) -> Project:
    p = s.get(Project, project_id)
    if p is None:
        raise NotFound(f"project {project_id} not found")
    return p


def add_items(s: Session, project: Project, rows: list[dict]) -> int:
    s.add_all(Item(project_id=project.id, **row) for row in rows)
    s.commit()
    return len(rows)


def get_or_create_rater(s: Session, name: str, is_model: bool = False) -> Rater:
    name = name.strip()
    if not name:
        raise ValueError("rater name is required")
    r = s.scalar(select(Rater).where(Rater.name == name))
    if r is None:
        r = Rater(name=name, is_model=is_model)
        s.add(r)
        s.commit()
    return r


def next_item(
    s: Session, project: Project, rater: Rater, rng: random.Random | None = None, skip: set[int] = frozenset()
) -> tuple[Item, bool] | None:
    """Pick the next pair for a rater and decide whether to show it swapped.

    Unlabeled-by-this-rater items that still need labels come first, fewest
    labels first, so coverage grows evenly. Gold items are shown to everyone.
    """
    counts = select(Label.item_id, func.count().label("n")).group_by(Label.item_id).subquery()
    n = func.coalesce(counts.c.n, 0)
    done = select(Label.item_id).where(Label.rater_id == rater.id)
    item = s.scalar(
        select(Item)
        .outerjoin(counts, counts.c.item_id == Item.id)
        .where(Item.project_id == project.id, Item.id.not_in(done), Item.id.not_in(skip), or_(Item.gold.is_not(None), n < project.overlap))
        .order_by(n, func.random())
        .limit(1)
    )
    if item is None:
        return None
    return item, (rng or random).random() < 0.5


def add_label(
    s: Session,
    item: Item,
    rater: Rater,
    score: int,
    criteria: dict[str, str],
    rationale: str = "",
    shown_swapped: bool = False,
    seconds: float | None = None,
) -> Label:
    label = Label(
        item_id=item.id,
        rater_id=rater.id,
        score=score,
        criteria=criteria,
        rationale=rationale,
        shown_swapped=shown_swapped,
        seconds=seconds,
    )
    s.add(label)
    try:
        s.commit()
    except IntegrityError:
        s.rollback()
        raise AlreadyLabeled(f"{rater.name} already labeled item {item.id}") from None
    return label


def _records(s: Session, project: Project) -> tuple[list[Item], list[LabelRec]]:
    items = list(s.scalars(select(Item).where(Item.project_id == project.id).order_by(Item.id)))
    rows = s.execute(
        select(Label, Rater.name)
        .join(Rater, Rater.id == Label.rater_id)
        .join(Item, Item.id == Label.item_id)
        .where(Item.project_id == project.id)
        .order_by(Label.id)
    )
    labels = [LabelRec(l.item_id, name, l.score, l.shown_swapped, l.seconds) for l, name in rows]
    return items, labels


def project_stats(s: Session, project: Project) -> ProjectStats:
    items, labels = _records(s, project)
    return compute_stats([ItemRec(i.id, i.gold) for i in items], labels, overlap=project.overlap)


def export_dpo(s: Session, project: Project, opts: ExportOptions) -> list[dict]:
    items, labels = _records(s, project)
    dicts = [
        {
            "id": i.id,
            "prompt": i.prompt,
            "response_a": i.response_a,
            "response_b": i.response_b,
            "model_a": i.model_a,
            "model_b": i.model_b,
            "gold": i.gold,
        }
        for i in items
    ]
    return dpo_pairs(dicts, labels, opts)


def export_labels(s: Session, project: Project) -> list[dict]:
    rows = s.execute(
        select(Label, Rater.name)
        .join(Rater, Rater.id == Label.rater_id)
        .join(Item, Item.id == Label.item_id)
        .where(Item.project_id == project.id)
        .order_by(Label.id)
    )
    return [
        {
            "item_id": l.item_id,
            "rater": name,
            "score": l.score,
            "criteria": l.criteria,
            "rationale": l.rationale,
            "shown_swapped": l.shown_swapped,
            "seconds": l.seconds,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l, name in rows
    ]
