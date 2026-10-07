import React, { useState } from "react";
import { CheckCircle2, FileCode, Plus, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Artifact, ArtifactVerifyResult } from "../types";

export const ArtifactRegistry: React.FC<{ artifacts: Artifact[]; runId?: string; onRefresh: () => void }> = ({ artifacts, runId, onRefresh }) => {
  const { isAnalyst } = useAuth();
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [res, setRes] = useState<ArtifactVerifyResult | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", type: "model_checkpoint", path: "", sha: "" });

  const handleVerify = async (id: string) => {
    setVerifyingId(id);
    try { setRes(await api.artifacts.verify(id)); onRefresh(); } catch (e: any) { alert(e.message); }
    finally { setVerifyingId(null); }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!runId) return;
    try {
      await api.artifacts.create(runId, { name: form.name, artifact_type: form.type, file_path: form.path, sha256_hash: form.sha, file_size_bytes: 1048576 });
      setShowAdd(false); setForm({ name: "", type: "model_checkpoint", path: "", sha: "" }); onRefresh();
    } catch (err: any) { alert(err.message); }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
      <div className="flex justify-between items-center mb-3">
        <div><h3 className="text-sm font-semibold text-white">Artifact Manifest & Integrity Registry</h3><p className="text-xs text-slate-400">Model checkpoints, predictions, and SHA-256 verification</p></div>
        {isAnalyst && runId && <button onClick={() => setShowAdd(true)} className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs flex items-center gap-1"><Plus className="w-3.5 h-3.5" />Register</button>}
      </div>

      {res && (
        <div className={`mb-3 p-2.5 rounded border text-xs flex justify-between items-center ${res.verified ? "bg-emerald-950/40 border-emerald-800 text-emerald-300" : "bg-rose-950/40 border-rose-800 text-rose-300"}`}>
          <div className="flex items-center gap-1.5">{res.verified ? <ShieldCheck className="w-4 h-4 text-emerald-400" /> : <ShieldAlert className="w-4 h-4 text-rose-400" />}<span><strong>{res.name}</strong>: {res.message}</span></div>
          <button onClick={() => setRes(null)}>×</button>
        </div>
      )}

      {!artifacts.length ? <div className="p-6 text-center bg-slate-950/40 rounded text-slate-400 text-xs">No artifacts registered.</div> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
              <tr><th className="p-2">Name</th><th className="p-2">Type</th><th className="p-2">Size</th><th className="p-2">SHA-256 Digest</th><th className="p-2 text-center">Status</th><th className="p-2 text-right">Action</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {artifacts.map(a => (
                <tr key={a.id} className="hover:bg-slate-800/30">
                  <td className="p-2 font-sans font-medium text-slate-200 flex items-center gap-1.5"><FileCode className="w-3.5 h-3.5 text-blue-400" /><span className="truncate max-w-xs">{a.name}</span></td>
                  <td className="p-2 text-slate-300"><span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px]">{a.artifact_type}</span></td>
                  <td className="p-2 text-slate-400">{a.file_size_bytes ? `${Math.round(a.file_size_bytes / 1048576)} MB` : "0 B"}</td>
                  <td className="p-2 text-slate-400 text-[11px] font-mono">{a.sha256_hash.slice(0, 8)}...{a.sha256_hash.slice(-6)}</td>
                  <td className="p-2 text-center">{a.verified ? <span className="text-emerald-400 inline-flex items-center gap-1 text-[11px]"><CheckCircle2 className="w-3 h-3" />Verified</span> : <span className="text-rose-400 text-[11px]">Unverified</span>}</td>
                  <td className="p-2 text-right"><button onClick={() => handleVerify(a.id)} disabled={verifyingId === a.id} className="px-2 py-0.5 bg-slate-800 text-slate-200 rounded border border-slate-700 text-[11px] font-sans inline-flex items-center gap-1"><RefreshCw className={`w-3 h-3 ${verifyingId === a.id ? "animate-spin" : ""}`} />Verify Checksum</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-5 space-y-3">
            <h4 className="text-sm font-bold text-white">Register Artifact</h4>
            <form onSubmit={handleCreate} className="space-y-2 text-xs">
              <div><label className="block text-slate-400 mb-1">Name</label><input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white" /></div>
              <div><label className="block text-slate-400 mb-1">Type</label><select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white"><option value="model_checkpoint">Model Checkpoint</option><option value="eval_predictions">Evaluation Predictions</option></select></div>
              <div><label className="block text-slate-400 mb-1">Path</label><input type="text" required value={form.path} onChange={e => setForm({ ...form, path: e.target.value })} className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white font-mono" /></div>
              <div><label className="block text-slate-400 mb-1">SHA-256</label><input type="text" required value={form.sha} onChange={e => setForm({ ...form, sha: e.target.value })} className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white font-mono" /></div>
              <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setShowAdd(false)} className="px-2.5 py-1 text-slate-400">Cancel</button><button type="submit" className="px-3 py-1 bg-blue-600 text-white rounded">Save</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
