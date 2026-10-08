"""FastAPI app. Everything lives under /api; the built React app is served at /."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import __version__, service
from .analysis import ExportOptions, canonicalize
from .db import Database
from .importer import PairFormatError, parse_pairs
from .models import Item, Label, Project, Rater

SAMPLE = Path(__file__).resolve().parent / "data" / "sample_pairs.jsonl"
FRONTEND_DIST = Path(
    os.environ.get("PREFSTUDIO_FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")
)


class RubricCriterion(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    label: str
    description: str = ""


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    rubric: list[RubricCriterion] | None = None
    overlap: int = Field(3, ge=1, le=50)


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    rubric: list[RubricCriterion]
    overlap: int
    n_items: int = 0
    n_labels: int = 0


class ImportIn(BaseModel):
    jsonl: str


class RaterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RaterOut(BaseModel):
    id: int
    name: str


class Assignment(BaseModel):
    item_id: int
    prompt: str
    left: str
    right: str
    swapped: bool
    labeled: int
    remaining: int


class LabelIn(BaseModel):
    item_id: int
    swapped: bool
    score: int = Field(ge=-2, le=2, description="negative = left response is better")
    criteria: dict[str, Literal["left", "right", "tie"]] = {}
    rationale: str = Field("", max_length=5000)
    seconds: float | None = Field(None, ge=0)


def create_app(database_url: str | None = None) -> FastAPI:
    db = Database(database_url)
    db.create_all()
    app = FastAPI(title="Preference Studio", version=__version__)
    app.state.db = db

    SessionDep = Annotated[Session, Depends(db.session)]

    def project_or_404(s: Session, project_id: int) -> Project:
        try:
            return service.get_project(s, project_id)
        except service.NotFound as e:
            raise HTTPException(404, str(e)) from None

    def current_rater(s: SessionDep, x_rater_id: Annotated[int | None, Header()] = None) -> Rater:
        rater = s.get(Rater, x_rater_id) if x_rater_id else None
        if rater is None:
            raise HTTPException(401, "sign in first (X-Rater-Id header)")
        return rater

    def to_out(s: Session, p: Project) -> ProjectOut:
        n_items = s.scalar(select(func.count()).select_from(Item).where(Item.project_id == p.id))
        n_labels = s.scalar(
            select(func.count()).select_from(Label).join(Item).where(Item.project_id == p.id)
        )
        return ProjectOut(
            id=p.id, name=p.name, description=p.description, rubric=p.rubric,
            overlap=p.overlap, n_items=n_items or 0, n_labels=n_labels or 0,
        )

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": __version__}

    @app.post("/api/raters", response_model=RaterOut)
    def sign_in(body: RaterIn, s: SessionDep):
        r = service.get_or_create_rater(s, body.name)
        return RaterOut(id=r.id, name=r.name)

    @app.get("/api/projects", response_model=list[ProjectOut])
    def list_projects(s: SessionDep):
        return [to_out(s, p) for p in s.scalars(select(Project).order_by(Project.id.desc()))]

    @app.post("/api/projects", response_model=ProjectOut, status_code=201)
    def create_project(body: ProjectIn, s: SessionDep):
        rubric = [c.model_dump() for c in body.rubric] if body.rubric else None
        p = service.create_project(s, body.name, body.description, rubric, body.overlap)
        return to_out(s, p)

    @app.post("/api/projects/sample", response_model=ProjectOut, status_code=201)
    def create_sample(s: SessionDep):
        p = service.create_project(
            s, "Sample: assistant responses",
            "Hand-written pairs covering facts, code, reasoning, safety and writing. 10 are gold checks.",
        )
        service.add_items(s, p, parse_pairs(SAMPLE.read_text(encoding="utf-8")))
        return to_out(s, p)

    @app.get("/api/projects/{project_id}", response_model=ProjectOut)
    def get_project(project_id: int, s: SessionDep):
        return to_out(s, project_or_404(s, project_id))

    @app.post("/api/projects/{project_id}/import")
    def import_pairs(project_id: int, body: ImportIn, s: SessionDep):
        p = project_or_404(s, project_id)
        try:
            rows = parse_pairs(body.jsonl)
        except PairFormatError as e:
            raise HTTPException(422, str(e)) from None
        return {"imported": service.add_items(s, p, rows)}

    @app.get("/api/projects/{project_id}/next", response_model=Assignment | None)
    def next_pair(project_id: int, s: SessionDep, rater: Annotated[Rater, Depends(current_rater)]):
        p = project_or_404(s, project_id)
        picked = service.next_item(s, p, rater)
        if picked is None:
            return None
        item, swapped = picked
        labeled = s.scalar(
            select(func.count()).select_from(Label).join(Item)
            .where(Item.project_id == p.id, Label.rater_id == rater.id)
        ) or 0
        total = s.scalar(select(func.count()).select_from(Item).where(Item.project_id == p.id)) or 0
        left, right = (item.response_b, item.response_a) if swapped else (item.response_a, item.response_b)
        return Assignment(
            item_id=item.id, prompt=item.prompt, left=left, right=right, swapped=swapped,
            labeled=labeled, remaining=total - labeled,
        )

    @app.post("/api/projects/{project_id}/labels", status_code=201)
    def submit_label(
        project_id: int, body: LabelIn, s: SessionDep, rater: Annotated[Rater, Depends(current_rater)]
    ):
        p = project_or_404(s, project_id)
        item = s.get(Item, body.item_id)
        if item is None or item.project_id != p.id:
            raise HTTPException(404, "item not found in this project")
        keys = {c["key"] for c in p.rubric}
        unknown = set(body.criteria) - keys
        if unknown:
            raise HTTPException(422, f"unknown rubric keys: {sorted(unknown)}")
        score, criteria = canonicalize(body.score, body.criteria, body.swapped)
        try:
            label = service.add_label(
                s, item, rater, score, criteria, body.rationale.strip(), body.swapped, body.seconds
            )
        except service.AlreadyLabeled as e:
            raise HTTPException(409, str(e)) from None
        return {"id": label.id, "score": score, "criteria": criteria}

    @app.get("/api/projects/{project_id}/stats")
    def stats(project_id: int, s: SessionDep):
        return asdict(service.project_stats(s, project_or_404(s, project_id)))

    @app.get("/api/projects/{project_id}/export/dpo")
    def export_dpo(
        project_id: int,
        s: SessionDep,
        min_labels: int = Query(1, ge=1),
        min_agreement: float = Query(0.0, ge=0, le=1),
        min_margin: float = Query(0.5, ge=0, le=2),
        include_gold: bool = False,
        exclude_raters: Annotated[list[str], Query()] = [],
    ):
        p = project_or_404(s, project_id)
        opts = ExportOptions(min_labels, min_agreement, min_margin, include_gold, tuple(exclude_raters))
        return _jsonl(service.export_dpo(s, p, opts), f"project-{p.id}-dpo.jsonl")

    @app.get("/api/projects/{project_id}/export/labels")
    def export_labels(project_id: int, s: SessionDep):
        p = project_or_404(s, project_id)
        return _jsonl(service.export_labels(s, p), f"project-{p.id}-labels.jsonl")

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "not found")
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


def _jsonl(rows: list[dict], filename: str) -> Response:
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    return Response(
        body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
