import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { user, loading, logout } = useAuth();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const detail = await api.createSession(url.trim());
      navigate(`/session/${detail.session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="home-page">
      <header className="home-header">
        <h1>CodeSync</h1>
        <p className="subtitle">Real-time collaborative code review, powered by CRDTs.</p>
        <div className="auth-bar">
          {loading ? null : user ? (
            <div className="user-chip">
              {user.avatar_url && <img src={user.avatar_url} alt={user.username} />}
              <span>{user.username}</span>
              <button onClick={logout}>Log out</button>
            </div>
          ) : (
            <a className="github-login-btn" href={api.githubLoginUrl()}>
              Log in with GitHub
            </a>
          )}
        </div>
      </header>

      <form className="url-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="https://github.com/owner/repo/blob/main/path/to/file.py"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Loading file..." : "Start session"}
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}

      <p className="hint">
        {user
          ? "You're logged in, so private repos you have access to will work too."
          : "Log in with GitHub to review files in private repositories."}
      </p>
    </div>
  );
}
