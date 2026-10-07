import React, { createContext, useContext, useEffect, useState } from "react";
import { api, setCsrfToken } from "../api/client";
import { UserProfile } from "../types";

interface AuthContextType {
  user: UserProfile | null; loading: boolean; error: string | null;
  isAdmin: boolean; isAnalyst: boolean; isViewer: boolean;
  switchDemoProfile: (role: "admin" | "analyst" | "viewer") => Promise<void>;
  logout: () => Promise<void>; refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = async () => {
    setLoading(true);
    try {
      setUser(await api.auth.getMe()); setError(null);
    } catch {
      try {
        const res = await api.auth.demoSwitch("analyst");
        setUser(res.user); setError(null);
      } catch { setUser(null); setError("OIDC login required"); }
    } finally { setLoading(false); }
  };

  useEffect(() => { refreshUser(); }, []);

  const switchDemoProfile = async (role: "admin" | "analyst" | "viewer") => {
    setLoading(true);
    try {
      const res = await api.auth.demoSwitch(role);
      setUser(res.user); setError(null);
    } catch (e: any) { setError(e.message || "Failed to switch persona"); }
    finally { setLoading(false); }
  };

  const logout = async () => {
    try { await api.auth.logout(); setCsrfToken(null); setUser(null); } catch {}
  };

  const roles = user?.roles || [];
  const isAdmin = roles.includes("admin");
  const isAnalyst = isAdmin || roles.includes("analyst");
  const isViewer = isAnalyst || roles.includes("viewer");

  return (
    <AuthContext.Provider value={{ user, loading, error, isAdmin, isAnalyst, isViewer, switchDemoProfile, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};
