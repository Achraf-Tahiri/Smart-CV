"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  clearToken,
  fetchMe,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  type User,
} from "@/lib/api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string): Promise<void> {
    await apiLogin(email, password);
    setUser(await fetchMe());
  }

  function logout(): void {
    void apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans <AuthProvider>.");
  return ctx;
}

/** Redirige vers /login si l'utilisateur n'est pas authentifié. */
export function useRequireAuth(): AuthState {
  const auth = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!auth.loading && !auth.user) router.replace("/login");
  }, [auth.loading, auth.user, router]);
  return auth;
}
