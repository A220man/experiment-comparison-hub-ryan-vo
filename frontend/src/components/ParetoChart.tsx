import React, { useState } from "react";
import { Award, Compass } from "lucide-react";
import { ParetoFrontierResult, ParetoPoint } from "../types";

export const ParetoChart: React.FC<{ data: ParetoFrontierResult; onSelectRun?: (runId: string) => void }> = ({ data, onSelectRun }) => {
  const [hov, setHov] = useState<ParetoPoint | null>(null);
  if (!data?.all_points.length) return <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400"><Compass className="w-8 h-8 mx-auto mb-2 text-slate-500 animate-pulse" /><p className="text-sm">No evaluated runs match objectives.</p></div>;

  const [ox, oy = data.objectives[0]] = data.objectives;
  const xs = data.all_points.map(p => p.metrics[ox.metric] ?? 0), ys = data.all_points.map(p => p.metrics[oy.metric] ?? 0);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const px = (maxX - minX) * 0.1 || (minX ? Math.abs(minX) * 0.1 : 1), py = (maxY - minY) * 0.1 || (minY ? Math.abs(minY) * 0.1 : 1);
  const x0 = minX - px, x1 = maxX + px, y0 = minY - py, y1 = maxY + py;
  const w = 640, h = 360, m = { t: 30, r: 30, b: 50, l: 70 }, iw = w - m.l - m.r, ih = h - m.t - m.b;
  const sx = (v: number) => m.l + ((v - x0) / (x1 - x0 || 1)) * iw, sy = (v: number) => m.t + ih - ((v - y0) / (y1 - y0 || 1)) * ih;
  const sf = [...data.frontier_points].sort((a, b) => (a.metrics[ox.metric] ?? 0) - (b.metrics[ox.metric] ?? 0));
  const fPath = sf.reduce((a, p, i) => `${a} ${i ? "L" : "M"} ${sx(p.metrics[ox.metric] ?? 0)} ${sy(p.metrics[oy.metric] ?? 0)}`, "");

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">Multi-Objective Pareto Trade-Off Frontier <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">Non-Dominated Skyline</span></h3>
          <p className="text-xs text-slate-400 mt-0.5">X: <strong className="text-slate-200">{ox.metric}</strong> ({ox.direction}) vs Y: <strong className="text-slate-200">{oy.metric}</strong> ({oy.direction})</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400">Hypervolume: <span className="font-mono font-bold text-blue-400">{data.hypervolume_indicator.toFixed(4)}</span></div>
          <div className="bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400">Frontier: <span className="font-mono font-bold text-emerald-400">{data.frontier_runs_count} / {data.total_evaluated_runs}</span></div>
          {data.knee_point && <div className="bg-amber-950/60 px-3 py-1.5 rounded-lg border border-amber-800 text-amber-300 flex items-center gap-1.5"><Award className="w-3.5 h-3.5 text-amber-400" /><span>Knee: {data.knee_point.variant_name}</span></div>}
        </div>
      </div>
      <div className="relative overflow-hidden bg-slate-950/50 rounded-lg border border-slate-800 p-2">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto select-none font-sans">
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => (
            <g key={`g-${i}`}>
              <line x1={m.l} y1={m.t + ih * (1 - pct)} x2={w - m.r} y2={m.t + ih * (1 - pct)} stroke="#1e293b" strokeDasharray="4 4" />
              <text x={m.l - 8} y={m.t + ih * (1 - pct) + 4} textAnchor="end" fill="#64748b" fontSize="10" fontFamily="monospace">{(y0 + (y1 - y0) * pct).toFixed(2)}</text>
              <line x1={m.l + iw * pct} y1={m.t} x2={m.l + iw * pct} y2={h - m.b} stroke="#1e293b" strokeDasharray="4 4" />
              <text x={m.l + iw * pct} y={h - m.b + 16} textAnchor="middle" fill="#64748b" fontSize="10" fontFamily="monospace">{(x0 + (x1 - x0) * pct).toFixed(2)}</text>
            </g>
          ))}
          {fPath && <path d={fPath} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="2 2" className="opacity-80" />}
          {data.all_points.map(pt => {
            const cx = sx(pt.metrics[ox.metric] ?? 0), cy = sy(pt.metrics[oy.metric] ?? 0);
            if (pt.is_knee_point) return <g key={pt.run_id} className="cursor-pointer" onClick={() => onSelectRun?.(pt.run_id)} onMouseEnter={() => setHov(pt)} onMouseLeave={() => setHov(null)}><circle cx={cx} cy={cy} r="10" fill="#f59e0b" fillOpacity="0.25" /><circle cx={cx} cy={cy} r="6" fill="#f59e0b" stroke="#fff" strokeWidth="2" /></g>;
            return <circle key={pt.run_id} cx={cx} cy={cy} r={pt.is_frontier ? 6 : 4} fill={pt.is_frontier ? "#10b981" : "#475569"} stroke={pt.is_frontier ? "#064e3b" : "#334155"} strokeWidth={pt.is_frontier ? 1.5 : 1} className={`cursor-pointer ${pt.is_frontier ? "" : "opacity-70"}`} onClick={() => onSelectRun?.(pt.run_id)} onMouseEnter={() => setHov(pt)} onMouseLeave={() => setHov(null)} />;
          })}
          <text x={m.l + iw / 2} y={h - 12} textAnchor="middle" fill="#94a3b8" fontSize="11" fontWeight="600">{ox.metric} ({ox.direction}) →</text>
          <text x={-(m.t + ih / 2)} y={18} transform="rotate(-90)" textAnchor="middle" fill="#94a3b8" fontSize="11" fontWeight="600">{oy.metric} ({oy.direction}) →</text>
        </svg>
        {hov && (
          <div className="absolute top-4 right-4 bg-slate-800/95 border border-slate-700 rounded-lg p-3 shadow-2xl text-xs backdrop-blur max-w-xs pointer-events-none">
            <div className="font-bold text-white mb-1">{hov.is_knee_point ? <span className="text-amber-400">★ Knee Point</span> : hov.is_frontier ? <span className="text-emerald-400">● Pareto Frontier</span> : <span className="text-slate-400">○ Dominated Point</span>}</div>
            <p className="font-semibold text-slate-200">{hov.run_name}</p>
            <p className="text-slate-400">{hov.variant_name} | Seed: {hov.seed}</p>
            <div className="mt-2 pt-2 border-t border-slate-700 font-mono text-slate-300">
              {Object.entries(hov.metrics).map(([k, v]) => <div key={k} className="flex justify-between"><span className="text-slate-400">{k}:</span><span>{v.toFixed(4)}</span></div>)}
            </div>
          </div>
        )}
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <div className="flex gap-4">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />Frontier</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" />Knee Point</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" />Dominated</span>
        </div>
        <p className="text-[11px] text-slate-500">Click any point to inspect run record</p>
      </div>
    </div>
  );
};
