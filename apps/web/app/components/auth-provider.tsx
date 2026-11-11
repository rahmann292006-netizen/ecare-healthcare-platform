"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getMe, hasSessionToken, login, logout, type UserLoginRequest, type UserRead } from "@/lib/api";

interface AuthContextValue { user: UserRead | null; loading: boolean; signIn: (input: UserLoginRequest) => Promise<UserRead>; signOut: () => Promise<void>; refreshUser: () => Promise<UserRead | null>; }
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshUser = useCallback(async () => {
    if (!hasSessionToken()) return null;
    try { return await getMe(); }
    catch (error) {
      if (error instanceof Error && error.message.startsWith("API 401")) {
        await logout();
      }
      return null;
    }
  }, []);
  useEffect(() => {
    let active = true;
    void Promise.resolve()
      .then(refreshUser)
      .then((current) => {
        if (!active) return;
        setUser(current);
        setLoading(false);
      });
    return () => { active = false; };
  }, [refreshUser]);
  const signIn = useCallback(async (input: UserLoginRequest) => { await login(input); const current = await getMe(); setUser(current); setLoading(false); return current; }, []);
  const signOut = useCallback(async () => { await logout(); setUser(null); }, []);
  const value = useMemo(() => ({ user, loading, signIn, signOut, refreshUser }), [user, loading, signIn, signOut, refreshUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
