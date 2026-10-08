import { useState } from "react";
import { api } from "../api";
import type { Rater } from "../types";

export default function SignIn({ onSignIn }: { onSignIn: (r: Rater) => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      onSignIn(await api.signIn(name.trim()));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form className="card narrow" onSubmit={submit}>
      <h1>Sign in to rate</h1>
      <p className="muted">Your name is attached to every label so agreement can be measured per rater.</p>
      <label className="field">
        Rater name
        <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. beki" />
      </label>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={!name.trim()}>
        Continue
      </button>
    </form>
  );
}
