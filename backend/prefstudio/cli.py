"""Command line: prefstudio serve | seed | ai-rate | stats | export."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import service
from .analysis import ExportOptions
from .api import SAMPLE
from .db import Database
from .importer import parse_pairs



def _fmt(x: float | None, pct: bool = False) -> str:
    if x is None:
        return "n/a"
    return f"{x:.0%}" if pct else f"{x:.3f}"


def cmd_serve(args) -> None:
    import uvicorn

    uvicorn.run("prefstudio.api:create_app", factory=True, host=args.host, port=args.port, reload=args.reload)


def cmd_seed(args, db: Database) -> None:
    rows = parse_pairs(Path(args.file).read_text(encoding="utf-8"))
    with db.sessionmaker() as s:
        p = service.create_project(s, args.name, args.description, overlap=args.overlap)
        n = service.add_items(s, p, rows)
        print(f"Created project {p.id} ({p.name!r}) with {n} pairs, {sum(1 for r in rows if r['gold'])} gold.")


def cmd_ai_rate(args, db: Database) -> None:
    from evalforge.models import get_model

    from .ai_rater import rate_project

    with db.sessionmaker() as s:
        project = service.get_project(s, args.project)
        for spec in args.model:
            model = get_model(spec)
            print(f"Rating project {project.id} with {model.name} (order: {args.order})")
            report = rate_project(s, project, model, order=args.order, limit=args.limit)
            summary = report.summary()
            print(json.dumps(summary, indent=2))
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                existing = json.loads(out.read_text()) if out.exists() else []
                out.write_text(json.dumps(existing + [summary], indent=2))


def cmd_stats(args, db: Database) -> None:
    with db.sessionmaker() as s:
        st = service.project_stats(s, service.get_project(s, args.project))
    if args.json:
        print(json.dumps(asdict(st), indent=2))
        return
    print(f"items {st.n_items}  labels {st.n_labels}  raters {st.n_raters}  fully labeled {st.items_fully_labeled}")
    print(
        f"percent agreement {_fmt(st.percent_agreement, True)}  "
        f"Krippendorff alpha nominal {_fmt(st.krippendorff_nominal)} / interval {_fmt(st.krippendorff_interval)}  "
        f"Fleiss kappa {_fmt(st.fleiss_kappa)}"
    )
    print(f"\n{'rater':<28}{'labels':>7}{'agree':>8}{'gold':>8}{'left':>7}{'ties':>7}")
    for r in st.raters:
        print(
            f"{r.rater:<28}{r.n_labels:>7}{_fmt(r.agreement_with_others, True):>8}"
            f"{_fmt(r.gold_accuracy, True):>8}{_fmt(r.left_bias, True):>7}{_fmt(r.tie_rate, True):>7}"
        )
    if st.pairwise_kappa:
        print("\npairwise Cohen's kappa")
        for p in st.pairwise_kappa:
            print(f"  {p['rater_a']} vs {p['rater_b']}: {_fmt(p['kappa'])} on {p['n_shared']} items")


def cmd_export(args, db: Database) -> None:
    with db.sessionmaker() as s:
        p = service.get_project(s, args.project)
        if args.kind == "dpo":
            opts = ExportOptions(args.min_labels, args.min_agreement, args.min_margin, args.include_gold, tuple(args.exclude_rater))
            rows = service.export_dpo(s, p, opts)
        else:
            rows = service.export_labels(s, p)
    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    for r in rows:
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
    if args.out:
        out.close()
        print(f"Wrote {len(rows)} records to {args.out}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="prefstudio", description=__doc__)
    ap.add_argument("--db", help="database URL (default: $DATABASE_URL or sqlite:///./prefstudio.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("serve", help="run the web app")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")

    p = sub.add_parser("seed", help="create a project from a JSONL file of pairs")
    p.add_argument("--file", default=str(SAMPLE))
    p.add_argument("--name", default="Sample: assistant responses")
    p.add_argument("--description", default="Hand-written pairs covering facts, code, reasoning, safety and writing.")
    p.add_argument("--overlap", type=int, default=3)

    p = sub.add_parser("ai-rate", help="label a project with one or more models")
    p.add_argument("project", type=int)
    p.add_argument("-m", "--model", action="append", required=True, help="e.g. ollama:qwen2.5:3b (repeatable)")
    p.add_argument("--order", choices=["both", "random"], default="both")
    p.add_argument("--limit", type=int)
    p.add_argument("-o", "--out", help="append the run summary to this JSON file")

    p = sub.add_parser("stats", help="print agreement statistics")
    p.add_argument("project", type=int)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("export", help="export DPO pairs or raw labels as JSONL")
    p.add_argument("project", type=int)
    p.add_argument("kind", choices=["dpo", "labels"])
    p.add_argument("-o", "--out")
    p.add_argument("--min-labels", type=int, default=1)
    p.add_argument("--min-agreement", type=float, default=0.0)
    p.add_argument("--min-margin", type=float, default=0.5)
    p.add_argument("--include-gold", action="store_true")
    p.add_argument("--exclude-rater", action="append", default=[])

    args = ap.parse_args(argv)
    if args.cmd == "serve":
        if args.db:
            import os

            os.environ["DATABASE_URL"] = args.db
        return cmd_serve(args)
    db = Database(args.db)
    db.create_all()
    try:
        {"seed": cmd_seed, "ai-rate": cmd_ai_rate, "stats": cmd_stats, "export": cmd_export}[args.cmd](args, db)
    except service.NotFound as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
