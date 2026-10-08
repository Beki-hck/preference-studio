import { useEffect, useState } from "react";
import { api, exportUrl } from "../api";
import { agreementLabel, num, pct } from "../format";
import type { Project, ProjectStats } from "../types";

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {hint && <div className="small muted">{hint}</div>}
    </div>
  );
}

function Split({ counts }: { counts: Record<"A" | "tie" | "B", number> }) {
  const total = counts.A + counts.tie + counts.B;
  if (!total) return <span className="muted small">no labels</span>;
  return (
    <div className="split" title={`A ${counts.A} · tie ${counts.tie} · B ${counts.B}`}>
      {(["A", "tie", "B"] as const).map((k) =>
        counts[k] ? <div key={k} className={`seg seg-${k}`} style={{ flexGrow: counts[k] }}>{counts[k]}</div> : null,
      )}
    </div>
  );
}

export default function Dashboard({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<Project | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [error, setError] = useState("");
  const [minLabels, setMinLabels] = useState(1);
  const [minAgreement, setMinAgreement] = useState(0);
  const [minMargin, setMinMargin] = useState(0.5);
  const [onlyDisagreements, setOnlyDisagreements] = useState(false);

  useEffect(() => {
    api.project(projectId).then(setProject).catch((e) => setError(e.message));
    api.stats(projectId).then(setStats).catch((e) => setError(e.message));
  }, [projectId]);

  if (error) return <p className="error">{error}</p>;
  if (!stats || !project) return <p className="muted">Loading…</p>;

  const items = onlyDisagreements
    ? stats.items.filter((i) => i.n_labels >= 2 && (i.agreement ?? 0) < 1)
    : stats.items;

  return (
    <section>
      <a href="#/" className="small muted">
        ← Projects
      </a>
      <div className="row between">
        <h1>{project.name}</h1>
        <a className="button primary" href={`#/p/${projectId}/label`}>
          Rate pairs
        </a>
      </div>

      <div className="tiles">
        <Tile label="Labels" value={String(stats.n_labels)} hint={`${stats.n_raters} raters`} />
        <Tile
          label="Fully labeled"
          value={`${stats.items_fully_labeled}/${stats.n_items}`}
          hint={`target ${project.overlap} per pair`}
        />
        <Tile label="Percent agreement" value={pct(stats.percent_agreement)} hint="pairs of raters who matched" />
        <Tile
          label="Krippendorff's α"
          value={num(stats.krippendorff_nominal)}
          hint={`${agreementLabel(stats.krippendorff_nominal)} · A / tie / B`}
        />
        <Tile
          label="α on 5-point scale"
          value={num(stats.krippendorff_interval)}
          hint={agreementLabel(stats.krippendorff_interval)}
        />
        <Tile label="Fleiss' κ" value={num(stats.fleiss_kappa)} hint="when every pair has equal labels" />
      </div>
      <p className="small muted">Agreement is computed on non-gold pairs; gold pairs measure rater accuracy instead.</p>

      <div className="card">
        <h2>Raters</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rater</th>
                <th>Labels</th>
                <th title="How often this rater matched the majority of the other raters">Agrees with others</th>
                <th title="Accuracy on gold pairs with a known answer">Gold accuracy</th>
                <th title="Share of non-tie picks that went to whichever response was shown on the left. 50% is unbiased.">
                  Picks left side
                </th>
                <th>Tie rate</th>
                <th>Median time</th>
              </tr>
            </thead>
            <tbody>
              {stats.raters.map((r) => (
                <tr key={r.rater}>
                  <td>{r.rater}</td>
                  <td>{r.n_labels}</td>
                  <td>{pct(r.agreement_with_others)}</td>
                  <td className={r.gold_accuracy != null && r.gold_accuracy < 0.8 ? "warn" : ""}>
                    {pct(r.gold_accuracy)} {r.n_gold ? <span className="muted small">({r.n_gold})</span> : null}
                  </td>
                  <td className={r.left_bias != null && Math.abs(r.left_bias - 0.5) > 0.2 ? "warn" : ""}>
                    {pct(r.left_bias)}
                  </td>
                  <td>{pct(r.tie_rate)}</td>
                  <td>{r.median_seconds == null ? "n/a" : `${Math.round(r.median_seconds)}s`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {stats.pairwise_kappa.length > 0 && (
          <>
            <h3>Pairwise Cohen's κ</h3>
            <ul className="pairs">
              {stats.pairwise_kappa.map((p) => (
                <li key={`${p.rater_a}-${p.rater_b}`}>
                  {p.rater_a} vs {p.rater_b}: <strong>{num(p.kappa)}</strong>{" "}
                  <span className="muted small">
                    ({agreementLabel(p.kappa)}, {p.n_shared} shared pairs)
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="card">
        <h2>Export DPO training data</h2>
        <p className="muted small">
          Each line is <code>{"{prompt, chosen, rejected, meta}"}</code>, the format TRL's DPOTrainer reads. The
          winner is decided by the mean score across raters.
        </p>
        <div className="filters">
          <label className="field">
            Min labels per pair
            <input type="number" min={1} value={minLabels} onChange={(e) => setMinLabels(Number(e.target.value))} />
          </label>
          <label className="field">
            Min agreement
            <input type="number" min={0} max={1} step={0.05} value={minAgreement}
              onChange={(e) => setMinAgreement(Number(e.target.value))} />
          </label>
          <label className="field">
            Min margin (drops near-ties)
            <input type="number" min={0} max={2} step={0.25} value={minMargin}
              onChange={(e) => setMinMargin(Number(e.target.value))} />
          </label>
        </div>
        <div className="row">
          <a className="button primary"
            href={exportUrl(projectId, "dpo", { min_labels: minLabels, min_agreement: minAgreement, min_margin: minMargin })}>
            Download DPO JSONL
          </a>
          <a className="button" href={exportUrl(projectId, "labels")}>
            Download raw labels
          </a>
        </div>
      </div>

      <div className="card">
        <div className="row between">
          <h2>Pairs</h2>
          <label className="row small">
            <input type="checkbox" checked={onlyDisagreements} onChange={(e) => setOnlyDisagreements(e.target.checked)} />
            Only show disagreements
          </label>
        </div>
        <div className="legend small">
          <span><i className="seg-A" /> A better</span>
          <span><i className="seg-tie" /> Tie</span>
          <span><i className="seg-B" /> B better</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Labels</th>
                <th>Split</th>
                <th>Majority</th>
                <th>Agreement</th>
                <th>Mean score</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.item_id}>
                  <td>
                    {i.item_id}
                    {i.gold && <span className="pill gold" title={`gold answer: ${i.gold}`}>gold</span>}
                  </td>
                  <td>{i.n_labels}</td>
                  <td className="split-cell"><Split counts={i.counts} /></td>
                  <td>{i.majority ?? "none"}</td>
                  <td className={i.agreement != null && i.n_labels >= 2 && i.agreement < 0.67 ? "warn" : ""}>
                    {pct(i.agreement)}
                  </td>
                  <td>{num(i.mean_score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
