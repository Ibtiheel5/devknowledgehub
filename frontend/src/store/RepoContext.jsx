import { createContext, useCallback, useContext, useMemo, useState } from "react";

const STORAGE_KEY = "dkh.active-repo";
const KNOWN_REPOS_KEY = "dkh.known-repos";

export const DEFAULT_REPO = "devknowledgehub-backend";

function readStorage(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage indisponible */
  }
}

const RepoContext = createContext(null);

export function RepoProvider({ children }) {
  const [activeRepo, setActiveRepoState] = useState(() =>
    readStorage(STORAGE_KEY, DEFAULT_REPO)
  );
  const [knownRepos, setKnownRepos] = useState(() => {
    const stored = readStorage(KNOWN_REPOS_KEY, []);
    return stored.includes(DEFAULT_REPO) ? stored : [DEFAULT_REPO, ...stored];
  });

  const setActiveRepo = useCallback((repoName) => {
    const trimmed = repoName?.trim();
    if (!trimmed) return;
    setActiveRepoState(trimmed);
    writeStorage(STORAGE_KEY, trimmed);
    setKnownRepos((prev) => {
      if (prev.includes(trimmed)) return prev;
      const next = [...prev, trimmed];
      writeStorage(KNOWN_REPOS_KEY, next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ activeRepo, setActiveRepo, knownRepos }),
    [activeRepo, setActiveRepo, knownRepos]
  );

  return <RepoContext.Provider value={value}>{children}</RepoContext.Provider>;
}

export function useRepo() {
  const context = useContext(RepoContext);

  if (!context) {
    throw new Error("useRepo doit être utilisé dans un RepoProvider.");
  }

  return context;
}
