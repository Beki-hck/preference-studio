import { useEffect, useState } from "react";
import { saveRater, savedRater } from "./api";
import type { Rater } from "./types";
import SignIn from "./pages/SignIn";
import Projects from "./pages/Projects";
import Label from "./pages/Label";
import Dashboard from "./pages/Dashboard";

/** Tiny hash router: #/, #/p/3/label, #/p/3/stats */
function useRoute(): string[] {
  const read = () => window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [parts, setParts] = useState(read);
  useEffect(() => {
    const on = () => setParts(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return parts;
}

export default function App() {
  const [rater, setRater] = useState<Rater | null>(savedRater);
  const route = useRoute();

  const signOut = () => {
    saveRater(null);
    setRater(null);
  };

  let page;
  if (!rater) {
    page = (
      <SignIn
        onSignIn={(r) => {
          saveRater(r);
          setRater(r);
        }}
      />
    );
  } else if (route[0] === "p" && route[2] === "label") {
    page = <Label projectId={Number(route[1])} rater={rater} />;
  } else if (route[0] === "p" && route[2] === "stats") {
    page = <Dashboard projectId={Number(route[1])} />;
  } else {
    page = <Projects />;
  }

  return (
    <>
      <header className="topbar">
        <a href="#/" className="brand">
          <span className="brand-mark" aria-hidden>
            ⇄
          </span>
          Preference Studio
        </a>
        {rater && (
          <div className="who">
            <span>{rater.name}</span>
            <button className="link" onClick={signOut}>
              Sign out
            </button>
          </div>
        )}
      </header>
      <main>{page}</main>
    </>
  );
}
