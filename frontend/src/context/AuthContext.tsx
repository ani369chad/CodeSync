import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

const ANON_NAME_KEY = "codesync_anon_name";
const ANON_COLOR_KEY = "codesync_anon_color";
const COLORS = ["#ef5350", "#42a5f5", "#66bb6a", "#ffa726", "#ab47bc", "#26c6da", "#ec407a", "#8d6e63"];

export function getDisplayIdentity(user: User | null): { name: string; color: string } {
  if (user) {
    let color = localStorage.getItem(ANON_COLOR_KEY);
    if (!color) {
      color = COLORS[Math.floor(Math.random() * COLORS.length)];
      localStorage.setItem(ANON_COLOR_KEY, color);
    }
    return { name: user.username, color };
  }

  let name = localStorage.getItem(ANON_NAME_KEY);
  if (!name) {
    name = `Guest-${Math.random().toString(36).slice(2, 6)}`;
    localStorage.setItem(ANON_NAME_KEY, name);
  }
  let color = localStorage.getItem(ANON_COLOR_KEY);
  if (!color) {
    color = COLORS[Math.floor(Math.random() * COLORS.length)];
    localStorage.setItem(ANON_COLOR_KEY, color);
  }
  return { name, color };
}
