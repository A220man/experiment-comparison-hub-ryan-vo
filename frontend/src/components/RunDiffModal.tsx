import React, { useEffect, useState } from "react";
import { ArrowRight, X } from "lucide-react";
import { api } from "../api/client";
import { RunDiffResult } from "../types";

export const RunDiffModal: React.FC<{ baseRunId: string; targetRunId: string; onClose: () => void }> = ({ baseRunId, targetRunId, onClose }) => {
  const [diff, setDiff] = useState<RunDiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try { setDiff(await api.runs.diff(baseRunId, targetRunId)); }
      catch (e: any) { setError(e.message || "Failed to load diff"); }
      finally { setLoading(false); }
    })();
  }, [baseRunId, targetRunId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div><h3 className="text-sm font-bold text-white">Pairwise Run Diff Analyzer</h3><p className="text-xs text-slate-400">Baseline vs Target parameter deltas and metric divergences</p></div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 overflow-y-auto space-y-4">
          {loading && <div className="py-8 text-center text-slate-400 text-xs">Computing deltas...</div>}
          {error && <div className="p-3 bg-rose-950/50 border border-rose-800 text-xs text-rose-300">{error}</div>}
          {diff && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] font-mono uppercase text-slate-400">Baseline</span>
                  <h4 className="font-semibold text-slate-200 text-xs">{diff.base_run.name}</h4>
                  <div className="flex gap-2 text-xs text-slate-400 font-mono"><span>{diff.base_run.variant_name}</span><span>seed:{diff.base_run.seed}</span></div>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] font-mono uppercase text-slate-400">Target</span>
                  <h4 className="font-semibold text-slate-200 text-xs">{diff.target_run.name}</h4>
                  <div className="flex gap-2 text-xs text-slate-400 font-mono"><span>{diff.target_run.variant_name}</span><span>seed:{diff.target_run.seed}</span></div>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase text-slate-400 font-mono mb-1">Metric Divergence</h4>
                <table className="w-full text-left text-xs bg-slate-950/40 rounded border border-slate-800">
                  <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                    <tr><th className="p-2">Metric</th><th className="p-2 text-right">Base</th><th className="p-2 text-right">Target</th><th className="p-2 text-right">Delta</th><th className="p-2 text-right">% Change</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {diff.metric_deltas.map((m, i) => (
                      <tr key={i} className="hover:bg-slate-800/30">
                        <td className="p-2 font-medium text-slate-200">{m.metric}</td>
                        <td className="p-2 text-right text-slate-400">{m.base_value !== null ? m.base_value.toFixed(4) : "—"}</td>
                        <td className="p-2 text-right text-slate-200 font-semibold">{m.target_value !== null ? m.target_value.toFixed(4) : "—"}</td>
                        <td className="p-2 text-right"><span className={m.improved === true ? "text-emerald-400 font-bold" : m.improved === false ? "text-rose-400 font-bold" : "text-slate-300"}>{m.absolute_delta !== null ? `${m.absolute_delta > 0 ? "+" : ""}${m.absolute_delta.toFixed(4)}` : "—"}</span></td>
                        <td className="p-2 text-right text-slate-300">{m.percent_change !== null ? `${m.percent_change > 0 ? "+" : ""}${m.percent_change.toFixed(2)}%` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase text-slate-400 font-mono mb-1">Hyperparameter Deltas</h4>
                <table className="w-full text-left text-xs bg-slate-950/40 rounded border border-slate-800">
                  <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                    <tr><th className="p-2">Parameter</th><th className="p-2">Base</th><th className="p-2"></th><th className="p-2">Target</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {diff.parameter_deltas.map((p, i) => (
                      <tr key={i} className={p.changed ? "bg-amber-950/20 text-amber-200" : "text-slate-400"}>
                        <td className="p-2 font-medium text-white">{p.parameter}</td>
                        <td className="p-2">{JSON.stringify(p.base_value)}</td>
                        <td className="p-2 text-center"><ArrowRight className={`w-3.5 h-3.5 ${p.changed ? "text-amber-400" : "text-slate-600"}`} /></td>
                        <td className="p-2 font-semibold text-slate-200">{JSON.stringify(p.target_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
