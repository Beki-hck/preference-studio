"""Use a language model as a rater (LLM-as-judge).

Model clients come from evalforge (project 1 of this portfolio), so any
``ollama:*``, ``openai:*`` or ``anthropic:*`` model works.

With ``order="both"`` each pair is judged twice, once in each order. A model
that flips its verdict when the order flips is showing position bias, so those
pairs are recorded as ties and counted in the report.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from . import service
from .models import Project

JUDGE_PROMPT = """You are rating two AI assistant responses to the same user prompt.

Judge them on: {criteria}.

[User prompt]
{prompt}

[Response 1]
{first}

[Response 2]
{second}

Think briefly about which response is better, in at most three sentences.
Then end with one line in exactly this format:
RATING: <n>
where <n> is 1 (Response 1 is much better), 2 (Response 1 is slightly better),
3 (they are equally good), 4 (Response 2 is slightly better) or 5 (Response 2 is much better)."""

_RATING = re.compile(r"RATING:\s*\**\s*([1-5])", re.IGNORECASE)


def parse_rating(text: str) -> int | None:
    """Return the rating as a displayed score: -2 (first much better) .. +2."""
    found = _RATING.findall(text)
    return int(found[-1]) - 3 if found else None


@dataclass
class RatingReport:
    rater: str
    order: str = "both"
    rated: int = 0
    unparseable: int = 0  # skipped: no RATING line in the answer
    inconsistent: int = 0  # verdict flipped when the order flipped (order="both")
    first_position_picks: int = 0  # decided raw verdicts that favored the first-shown response
    decided_verdicts: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "rater": self.rater,
            "order": self.order,
            "rated": self.rated,
            "unparseable": self.unparseable,
            "order_consistency": (1 - self.inconsistent / self.rated) if self.order == "both" and self.rated else None,
            "first_position_rate": (self.first_position_picks / self.decided_verdicts) if self.decided_verdicts else None,
            "errors": self.errors[:5],
        }


def combine(score_ab: int, score_ba_canonical: int) -> tuple[int, bool]:
    """Merge the two canonical scores from both orders. Returns (score, consistent)."""
    if score_ab * score_ba_canonical < 0:
        return 0, False
    return int((score_ab + score_ba_canonical) / 2), True  # rounds toward a tie


def rate_project(
    s: Session,
    project: Project,
    model,
    order: str = "both",
    limit: int | None = None,
    rng: random.Random | None = None,
    log=print,
) -> RatingReport:
    rng = rng or random.Random(0)
    rater = service.get_or_create_rater(s, f"ai:{model.name}", is_model=True)
    report = RatingReport(rater.name, order)
    skip: set[int] = set()
    criteria = "; ".join(f"{c['label']} ({c['description']})" for c in project.rubric)

    def ask(prompt: str, first: str, second: str) -> tuple[int | None, str]:
        text = model.generate(JUDGE_PROMPT.format(criteria=criteria, prompt=prompt, first=first, second=second))
        return parse_rating(text), text.strip()

    while limit is None or report.rated < limit:
        picked = service.next_item(s, project, rater, rng, skip)
        if picked is None:
            break
        item, swapped = picked
        try:
            if order == "both":
                d1, t1 = ask(item.prompt, item.response_a, item.response_b)
                d2, t2 = ask(item.prompt, item.response_b, item.response_a)
                if d1 is None or d2 is None:
                    report.unparseable += 1
                    skip.add(item.id)
                    continue
                for d in (d1, d2):
                    if d != 0:
                        report.decided_verdicts += 1
                        report.first_position_picks += d < 0
                score, ok = combine(d1, -d2)
                report.inconsistent += not ok
                rationale = (t1 if ok else "Verdict changed when the order changed; recorded as a tie.\n\n" + t1)[:2000]
                swapped = None  # saw both orders, so no single side was "left"
            else:
                first, second = (item.response_b, item.response_a) if swapped else (item.response_a, item.response_b)
                d, rationale = ask(item.prompt, first, second)
                if d is None:
                    report.unparseable += 1
                    skip.add(item.id)
                    continue
                if d != 0:
                    report.decided_verdicts += 1
                    report.first_position_picks += d < 0
                score = -d if swapped else d
                rationale = rationale[:2000]
        except Exception as e:  # a failed call shouldn't kill a long run
            report.errors.append(f"item {item.id}: {e}")
            log(f"  item {item.id}: error {e}")
            break
        service.add_label(s, item, rater, score, {}, rationale, swapped)
        report.rated += 1
        log(f"  item {item.id}: score {score:+d}")
    return report
