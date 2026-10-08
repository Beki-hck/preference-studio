import { useEffect, useState } from "react";
import { api } from "../api";
import type { Project } from "../types";

export default function Projects() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);

  const load = () => api.projects().then(setProjects).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const sample = async () => {
    try {
      await api.createSample();
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <section>
      <div className="row between">
        <h1>Projects</h1>
        <div className="row">
          <button onClick={sample}>Load sample project</button>
          <button className="primary" onClick={() => setShowNew((v) => !v)}>
            New project
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {showNew && (
        <NewProject
          onDone={() => {
            setShowNew(false);
            load();
          }}
        />
      )}
      {projects?.length === 0 && !showNew && (
        <div className="card empty">
          <p>No projects yet. Load the sample project to try it, or create one and import a JSONL file of pairs.</p>
        </div>
      )}
      <div className="grid">
        {projects?.map((p) => {
          const target = p.n_items * p.overlap;
          const progress = target ? Math.min(1, p.n_labels / target) : 0;
          return (
            <article key={p.id} className="card project">
              <h2>{p.name}</h2>
              <p className="muted">{p.description || "No description"}</p>
              <div className="meter" aria-label="labeling progress">
                <div style={{ width: `${progress * 100}%` }} />
              </div>
              <p className="small muted">
                {p.n_items} pairs · {p.n_labels} labels · {p.overlap} raters per pair
              </p>
              <div className="row">
                <a className="button primary" href={`#/p/${p.id}/label`}>
                  Start rating
                </a>
                <a className="button" href={`#/p/${p.id}/stats`}>
                  Agreement &amp; export
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function NewProject({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [overlap, setOverlap] = useState(3);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const jsonl = file ? await file.text() : "";
      const p = await api.createProject({ name, description, overlap });
      if (jsonl) await api.importPairs(p.id, jsonl);
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h2>New project</h2>
      <label className="field">
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label className="field">
        Description
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label className="field">
        Raters per pair
        <input type="number" min={1} max={50} value={overlap} onChange={(e) => setOverlap(Number(e.target.value))} />
      </label>
      <label className="field">
        Pairs (JSONL with prompt, response_a, response_b and optional gold)
        <input type="file" accept=".jsonl,.json,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </label>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={!name.trim()}>
        Create
      </button>
    </form>
  );
}
