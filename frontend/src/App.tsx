import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import HomePage from "./pages/HomePage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import SessionPage from "./pages/SessionPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="/session/:sessionId" element={<SessionPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
