"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, setCsrfToken } from "@/lib/client";
import type { AuthResponse, MeResponse, SelfUser } from "@/lib/types";

interface AuthContextValue {
  user: SelfUser | null;
  setSession: (payload: AuthResponse | MeResponse) => void;
  refresh: () => Promise<SelfUser | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({
  initialUser,
  initialCsrf,
  children,
}: {
  initialUser: SelfUser | null;
  initialCsrf: string | null;
  children: ReactNode;
}) {
  const [user, setUser] = useState<SelfUser | null>(initialUser);

  useEffect(() => {
    setCsrfToken(initialCsrf);
  }, [initialCsrf]);

  const setSession = useCallback((payload: AuthResponse | MeResponse) => {
    setUser(payload.user);
    setCsrfToken(payload.csrf_token);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const payload = await api<MeResponse>("/api/v1/auth/me");
      setUser(payload.user);
      setCsrfToken(payload.csrf_token);
      return payload.user;
    } catch {
      setUser(null);
      setCsrfToken(null);
      return null;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      setCsrfToken(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, setSession, refresh, logout }),
    [user, setSession, refresh, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
