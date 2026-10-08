import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { splitBlocks } from "../format";
import type { Assignment, Project, Rater, Side } from "../types";

const SCALE = [
  { score: -2, label: "1 is much better" },
  { score: -1, label: "1 is slightly better" },
  { score: 0, label: "About the same" },
  { score: 1, label: "2 is slightly better" },
  { score: 2, label: "2 is much better" },
];

function Rich({ text }: { text: string }) {
  return (
    <>
      {splitBlocks(text).map((b, i) =>
        b.kind === "code" ? (
          <pre key={i}>
            <code>{b.text}</code>
          </pre>
        ) : (
          <p key={i} className="prose">
            {b.text}
          </p>
        ),
      )}
    </>
  );
}

export default function Label({ projectId, rater }: { projectId: number; rater: Rater }) {
  const [project, setProject] = useState<Project | null>(null);
  const [item, setItem] = useState<Assignment | null | undefined>(undefined);
  const [score, setScore] = useState<number | null>(null);
  const [criteria, setCriteria] = useState<Record<string, Side>>({});
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const started = useRef(Date.now());

  const loadNext = useCallback(async () => {
    setScore(null);
    setCriteria({});
    setRationale("");
    setError("");
    try {
      setItem(await api.next(projectId, rater));
      started.current = Date.now();
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError((e as Error).message);
    }
  }, [projectId, rater]);

  useEffect(() => {
    api.project(projectId).then(setProject).catch((e) => setError(e.message));
    loadNext();
  }, [projectId, loadNext]);

  const submit = useCallback(async () => {
    if (!item || score === null || saving) return;
    setSaving(true);
    try {
      await api.submit(projectId, rater, {
        item_id: item.item_id,
        swapped: item.swapped,
        score,
        criteria,
        rationale,
        seconds: (Date.now() - started.current) / 1000,
      });
      await loadNext();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }, [item, score, criteria, rationale, saving, projectId, rater, loadNext]);

  // Keys 1-5 pick the overall rating, Ctrl/Cmd+Enter submits.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        submit();
        return;
      }
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      const n = Number(e.key);
      if (n >= 1 && n <= 5) setScore(n - 3);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [submit]);

  if (item === undefined) return <p className="muted">{error || "Loading…"}</p>;

  if (item === null)
    return (
      <div className="card narrow empty">
        <h1>All done</h1>
        <p className="muted">There are no more pairs for you in this project. Thank you!</p>
        <a className="button primary" href={`#/p/${projectId}/stats`}>
          See agreement
        </a>
      </div>
    );

  const total = item.labeled + item.remaining;

  return (
    <section className="label-page">
      <div className="row between">
        <div>
          <a href="#/" className="small muted">
            ← Projects
          </a>
          <h1>{project?.name ?? "Rate"}</h1>
        </div>
        <span className="pill">
          {item.labeled} of {total} rated
        </span>
      </div>

      <div className="card prompt">
        <div className="eyebrow">Prompt</div>
        <Rich text={item.prompt} />
      </div>

      <div className="pair">
        {(["left", "right"] as const).map((side, i) => (
          <div key={side} className="card response">
            <div className="eyebrow">Response {i + 1}</div>
            <Rich text={item[side]} />
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Rubric</h2>
        <div className="rubric">
          {project?.rubric.map((c) => (
            <div key={c.key} className="criterion">
              <div>
                <strong>{c.label}</strong>
                <div className="small muted">{c.description}</div>
              </div>
              <div className="segmented" role="radiogroup" aria-label={c.label}>
                {(
                  [
                    ["left", "1"],
                    ["tie", "Same"],
                    ["right", "2"],
                  ] as const
                ).map(([value, text]) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={criteria[c.key] === value}
                    className={criteria[c.key] === value ? "on" : ""}
                    onClick={() => setCriteria({ ...criteria, [c.key]: value })}
                  >
                    {text}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <h2>Overall, which response is better?</h2>
        <div className="scale" role="radiogroup" aria-label="Overall preference">
          {SCALE.map((s, i) => (
            <button
              key={s.score}
              type="button"
              role="radio"
              aria-checked={score === s.score}
              className={score === s.score ? "on" : ""}
              onClick={() => setScore(s.score)}
            >
              <kbd>{i + 1}</kbd>
              {s.label}
            </button>
          ))}
        </div>

        <label className="field">
          Why? (optional, but rationales make the data far more useful)
          <textarea rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <div className="row between">
          <span className="small muted">Keys 1–5 pick a rating · Ctrl+Enter submits</span>
          <button className="primary" disabled={score === null || saving} onClick={submit}>
            Submit &amp; next
          </button>
        </div>
      </div>
    </section>
  );
}
