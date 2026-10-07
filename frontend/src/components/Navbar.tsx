import React from "react";
import { Activity, Shield, User, LogOut, FileText } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface NavbarProps {
  onOpenAuditLogs?: () => void;
  onNavigateHome?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenAuditLogs, onNavigateHome }) => {
  const { user, isAdmin, switchDemoProfile, logout } = useAuth();
  const currentRole = user?.roles[0] || "viewer";

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onNavigateHome}>
          <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              Experiment Comparison Hub
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900/60 text-blue-300 border border-blue-700/50">v0.1.0</span>
            </h1>
            <p className="text-xs text-slate-400">Ryan Vo | AI & Machine Learning</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {isAdmin && onOpenAuditLogs && (
            <button onClick={onOpenAuditLogs} className="px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-md border border-slate-700 flex items-center gap-1.5 transition-colors">
              <FileText className="w-3.5 h-3.5 text-slate-400" />Audit Trail
            </button>
          )}

          {user?.is_demo && (
            <div className="flex items-center space-x-1.5 bg-slate-800/80 p-1 rounded-lg border border-slate-700 text-xs">
              <span className="text-slate-400 px-2 font-mono text-[11px] flex items-center gap-1"><Shield className="w-3 h-3 text-amber-400" />DEMO:</span>
              {(["viewer", "analyst", "admin"] as const).map(role => (
                <button key={role} onClick={() => switchDemoProfile(role)} className={`px-2 py-1 rounded text-xs transition-colors capitalize ${currentRole === role ? (role === "admin" ? "bg-purple-600 text-white font-semibold" : role === "analyst" ? "bg-blue-600 text-white font-semibold" : "bg-slate-600 text-white font-semibold") : "text-slate-400 hover:text-slate-200"}`}>
                  {role}
                </button>
              ))}
            </div>
          )}

          {user ? (
            <div className="flex items-center space-x-3 border-l border-slate-800 pl-4">
              <div className="text-right">
                <p className="text-xs font-medium text-slate-200">{user.name}</p>
                <div className="flex items-center justify-end gap-1">
                  <span className="text-[10px] text-slate-400 font-mono">{user.email}</span>
                  <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">{user.roles[0]}</span>
                </div>
              </div>
              <button onClick={logout} title="Logout" className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-md transition-colors"><LogOut className="w-4 h-4" /></button>
            </div>
          ) : (
            <div className="text-xs text-slate-400 flex items-center gap-1.5"><User className="w-4 h-4" />Not authenticated</div>
          )}
        </div>
      </div>
    </header>
  );
};
