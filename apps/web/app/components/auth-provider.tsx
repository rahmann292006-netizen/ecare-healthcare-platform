"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getMe, hasSessionToken, login, logout, type UserLoginRequest, type UserRead } from "@/lib/api";

interface AuthContextValue { user: UserRead | null; loading: boolean; signIn: (input: UserLoginRequest) => Promise<UserRead>; signOut: () => Promise<void>; refreshUser: () => Promise<UserRead | null>; }
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshUser = useCallback(async () => {
    if (!hasSessionToken()) { setUser(null); setLoading(false); return null; }
    try { const current = await getMe(); setUser(current); return current; }
    catch { await logout(); setUser(null); return null; }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refreshUser(); }, [refreshUser]);
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
