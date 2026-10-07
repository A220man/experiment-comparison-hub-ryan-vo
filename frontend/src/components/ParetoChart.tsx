import React, { useState } from "react";
import { Award, Compass } from "lucide-react";
import { ParetoFrontierResult, ParetoPoint } from "../types";

export const ParetoChart: React.FC<{ data: ParetoFrontierResult; onSelectRun?: (runId: string) => void }> = ({ data, onSelectRun }) => {
  const [hoveredPoint, setHoveredPoint] = useState<ParetoPoint | null>(null);

  if (!data || !data.all_points.length) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <Compass className="w-8 h-8 mx-auto mb-2 text-slate-500 animate-pulse" /><p className="text-sm">No evaluated runs match objectives.</p>
      </div>
    );
  }

  const objX = data.objectives[0], objY = data.objectives[1] || data.objectives[0];
  const xVals = data.all_points.map(p => p.metrics[objX.metric] ?? 0);
  const yVals = data.all_points.map(p => p.metrics[objY.metric] ?? 0);
  const minX = Math.min(...xVals), maxX = Math.max(...xVals), minY = Math.min(...yVals), maxY = Math.max(...yVals);
  const padX = (maxX - minX) * 0.1 || (minX !== 0 ? Math.abs(minX) * 0.1 : 1);
  const padY = (maxY - minY) * 0.1 || (minY !== 0 ? Math.abs(minY) * 0.1 : 1);
  const dXMin = minX - padX, dXMax = maxX + padX, dYMin = minY - padY, dYMax = maxY + padY;

  const w = 640, h = 360, m = { top: 30, right: 30, bottom: 50, left: 70 };
  const innerW = w - m.left - m.right, innerH = h - m.top - m.bottom;
  const scaleX = (v: number) => m.left + ((v - dXMin) / (dXMax - dXMin || 1)) * innerW;
  const scaleY = (v: number) => m.top + innerH - ((v - dYMin) / (dYMax - dYMin || 1)) * innerH;

  const sortedFrontier = [...data.frontier_points].sort((a, b) => (a.metrics[objX.metric] ?? 0) - (b.metrics[objX.metric] ?? 0));
  const frontierPath = sortedFrontier.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${scaleX(pt.metrics[objX.metric] ?? 0)} ${scaleY(pt.metrics[objY.metric] ?? 0)}`, "");

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">Multi-Objective Pareto Trade-Off Frontier <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">Non-Dominated Skyline</span></h3>
          <p className="text-xs text-slate-400 mt-0.5">X: <strong className="text-slate-200">{objX.metric}</strong> ({objX.direction}) vs Y: <strong className="text-slate-200">{objY.metric}</strong> ({objY.direction})</p>
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
              <line x1={m.left} y1={m.top + innerH * (1 - pct)} x2={w - m.right} y2={m.top + innerH * (1 - pct)} stroke="#1e293b" strokeDasharray="4 4" />
              <text x={m.left - 8} y={m.top + innerH * (1 - pct) + 4} textAnchor="end" fill="#64748b" fontSize="10" fontFamily="monospace">{(dYMin + (dYMax - dYMin) * pct).toFixed(2)}</text>
              <line x1={m.left + innerW * pct} y1={m.top} x2={m.left + innerW * pct} y2={h - m.bottom} stroke="#1e293b" strokeDasharray="4 4" />
              <text x={m.left + innerW * pct} y={h - m.bottom + 16} textAnchor="middle" fill="#64748b" fontSize="10" fontFamily="monospace">{(dXMin + (dXMax - dXMin) * pct).toFixed(2)}</text>
            </g>
          ))}
          {frontierPath && <path d={frontierPath} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="2 2" className="opacity-80" />}
          {data.all_points.map(pt => {
            const cx = scaleX(pt.metrics[objX.metric] ?? 0), cy = scaleY(pt.metrics[objY.metric] ?? 0);
            if (pt.is_knee_point) return <g key={pt.run_id} className="cursor-pointer" onClick={() => onSelectRun?.(pt.run_id)} onMouseEnter={() => setHoveredPoint(pt)} onMouseLeave={() => setHoveredPoint(null)}><circle cx={cx} cy={cy} r="10" fill="#f59e0b" fillOpacity="0.25" /><circle cx={cx} cy={cy} r="6" fill="#f59e0b" stroke="#fff" strokeWidth="2" /></g>;
            if (pt.is_frontier) return <circle key={pt.run_id} cx={cx} cy={cy} r="6" fill="#10b981" stroke="#064e3b" strokeWidth="1.5" className="cursor-pointer" onClick={() => onSelectRun?.(pt.run_id)} onMouseEnter={() => setHoveredPoint(pt)} onMouseLeave={() => setHoveredPoint(null)} />;
            return <circle key={pt.run_id} cx={cx} cy={cy} r="4" fill="#475569" stroke="#334155" strokeWidth="1" className="cursor-pointer opacity-70" onClick={() => onSelectRun?.(pt.run_id)} onMouseEnter={() => setHoveredPoint(pt)} onMouseLeave={() => setHoveredPoint(null)} />;
          })}
          <text x={m.left + innerW / 2} y={h - 12} textAnchor="middle" fill="#94a3b8" fontSize="11" fontWeight="600">{objX.metric} ({objX.direction}) →</text>
          <text x={-(m.top + innerH / 2)} y={18} transform="rotate(-90)" textAnchor="middle" fill="#94a3b8" fontSize="11" fontWeight="600">{objY.metric} ({objY.direction}) →</text>
        </svg>

        {hoveredPoint && (
          <div className="absolute top-4 right-4 bg-slate-800/95 border border-slate-700 rounded-lg p-3 shadow-2xl text-xs backdrop-blur max-w-xs pointer-events-none">
            <div className="font-bold text-white mb-1">{hoveredPoint.is_knee_point ? <span className="text-amber-400">★ Knee Point</span> : hoveredPoint.is_frontier ? <span className="text-emerald-400">● Pareto Frontier</span> : <span className="text-slate-400">○ Dominated Point</span>}</div>
            <p className="font-semibold text-slate-200">{hoveredPoint.run_name}</p>
            <p className="text-slate-400">{hoveredPoint.variant_name} | Seed: {hoveredPoint.seed}</p>
            <div className="mt-2 pt-2 border-t border-slate-700 font-mono text-slate-300">
              {Object.entries(hoveredPoint.metrics).map(([k, v]) => <div key={k} className="flex justify-between"><span className="text-slate-400">{k}:</span><span>{v.toFixed(4)}</span></div>)}
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
