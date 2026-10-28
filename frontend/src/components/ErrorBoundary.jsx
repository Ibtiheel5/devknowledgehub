import { Component } from "react";

// Affiche l'erreur au lieu d'une page blanche quand un composant plante au rendu.
export class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Erreur de rendu :", error, info?.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div style={{ padding: 32, fontFamily: "system-ui, sans-serif", maxWidth: 800 }}>
        <h1 style={{ color: "#c2403a", fontSize: 22 }}>Une erreur est survenue dans l'interface</h1>
        <pre style={{ whiteSpace: "pre-wrap", background: "#fbe9e8", padding: 16, borderRadius: 8 }}>
          {String(error?.stack || error?.message || error)}
        </pre>
        <button
          type="button"
          onClick={() => {
            try {
              window.localStorage.removeItem("dkh.active-repo");
              window.localStorage.removeItem("dkh.known-repos");
            } catch { /* ignore */ }
            window.location.href = "/";
          }}
          style={{ padding: "8px 14px", cursor: "pointer" }}
        >
          Réinitialiser et recharger
        </button>
      </div>
    );
  }
}
