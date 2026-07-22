import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AuthCallbackPage() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    refresh().then(() => navigate("/"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="centered-page">
      <p>Signing you in&hellip;</p>
    </div>
  );
}
