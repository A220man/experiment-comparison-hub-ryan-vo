import React from "react";
import { Trophy, TrendingUp, TrendingDown, Target, BarChart2, HelpCircle } from "lucide-react";
import { LeaderboardResult, LeaderboardEntry } from "../types";

const bBg = "bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400";
const bPri = "bg-blue-600 hover:bg-blue-500 text-white";
const bSec = "bg-slate-800 hover:bg-slate-700 text-slate-300";
const card = "bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl";
const td = "p-2";
const tdM = "p-2 font-mono text-[11px]";

const formatScore = (v: number) => v.toFixed(3);
const formatPValue = (p: number) => p < 0.001 ? "< 0.001" : p.toFixed(4);
const formatD = (d: number) => d.toFixed(2);

export const Leaderboard: React.FC<{ data: LeaderboardResult | null }> = ({ data }) => {
  if (!data?.leaderboard?.length) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <BarChart2 className="w-8 h-8 mx-auto mb-2 text-slate-500 animate-pulse" />
        <p className="text-sm">No variant data available for leaderboard.</p>
        <p className="text-xs text-slate-500 mt-1">Log runs with multiple variants to compute rankings.</p>
      </div>
    );
  }

  const objectives = data.objectives;
  const objLabels = objectives.map(o => `${o.metric} (${o.direction})`).join(" vs ");

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            Multi-Metric Composite Ranking & Variant Leaderboard
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
              {data.is_aggregated ? `Variant-Aggregated (${data.aggregation_method || "mean"})` : "Raw Runs"}
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Objectives: <strong className="text-slate-200">{objLabels}</strong></p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className={bBg}>Weight: Pareto <span className="font-mono font-bold text-blue-400">{Math.round(data.weight_pareto * 100)}%</span> / Significance <span className="font-mono font-bold text-amber-400">{Math.round(data.weight_significance * 100)}%</span></div>
          <div className={bBg}>Variants: <span className="font-mono font-bold text-emerald-400">{data.total_variants}</span></div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800 sticky top-0">
            <tr>
              <th className={td}>Rank</th>
              <th className={td}>Variant</th>
              <th className={tdM}>Composite</th>
              <th className={tdM}>Pareto</th>
              <th className={tdM}>Significance</th>
              <th className={tdM}>Frontier</th>
              <th className={tdM}>Knee</th>
              {objectives.map((obj, i) => (
                <th key={i} className={tdM}>{obj.metric}</th>
              ))}
              <th className={tdM}>N (seeds)</th>
              <th className={tdM}>p-value</th>
              <th className={tdM}>Cohen's d</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {data.leaderboard.map((entry: LeaderboardEntry) => (
              <tr key={entry.variant_name} className={`hover:bg-slate-800/40 ${entry.is_baseline ? "bg-slate-950/50" : ""}`}>
                <td className={td}>
                  <span className={`font-bold ${entry.rank === 1 ? "text-amber-400" : entry.rank === 2 ? "text-slate-300" : entry.rank === 3 ? "text-amber-600" : "text-slate-400"}`}>
                    #{entry.rank}
                    {entry.rank === 1 && <Trophy className="w-3.5 h-3.5 inline ml-1 text-amber-400" />}
                    {entry.rank === 2 && <TrendingUp className="w-3.5 h-3.5 inline ml-1 text-slate-300" />}
                    {entry.rank === 3 && <TrendingDown className="w-3.5 h-3.5 inline ml-1 text-amber-600" />}
                  </span>
                </td>
                <td className={`${td} font-semibold text-white`}>
                  {entry.is_baseline && <span className="mr-1.5 px-1.5 py-0.5 text-[10px] bg-slate-800 text-slate-300 rounded font-mono">BASELINE</span>}
                  {entry.variant_name}
                </td>
                <td className={tdM}>
                  <span className={`font-mono font-bold ${entry.composite_score >= 0.7 ? "text-emerald-400" : entry.composite_score >= 0.4 ? "text-amber-400" : "text-rose-400"}`}>
                    {formatScore(entry.composite_score)}
                  </span>
                </td>
                <td className={tdM}>
                  <span className="font-mono text-blue-400">{formatScore(entry.pareto_score)}</span>
                </td>
                <td className={tdM}>
                  <span className="font-mono text-amber-400">{formatScore(entry.significance_score)}</span>
                </td>
                <td className={tdM}>
                  {entry.is_frontier ? (
                    <span className="text-emerald-400 font-bold">● Frontier</span>
                  ) : (
                    <span className="text-slate-500">○ Dominated</span>
                  )}
                </td>
                <td className={tdM}>
                  {entry.is_knee_point ? (
                    <span className="text-amber-400 font-bold flex items-center gap-1"><Target className="w-3 h-3" /> Knee</span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
                {objectives.map((obj, i) => (
                  <td key={i} className={tdM}>
                    <span className={`font-mono ${entry.metrics[obj.metric] !== undefined ? (entry.is_frontier ? "text-emerald-300" : "text-slate-300") : "text-slate-500"}`}>
                      {entry.metrics[obj.metric] !== undefined ? entry.metrics[obj.metric].toFixed(4) : "—"}
                    </span>
                  </td>
                ))}
                <td className={tdM}>
                  <span className="font-mono text-slate-300">{entry.sample_size_n}</span>
                  <span className="text-slate-500 ml-1">({entry.seeds.join(", ")})</span>
                </td>
                <td className={tdM}>
                  <span className={`font-mono ${entry.avg_welch_p_value < 0.05 ? "text-emerald-400" : entry.avg_welch_p_value < 0.1 ? "text-amber-400" : "text-rose-400"}`}>
                    {formatPValue(entry.avg_welch_p_value)}
                  </span>
                </td>
                <td className={tdM}>
                  <span className={`font-mono ${entry.avg_cohens_d > 0.8 ? "text-emerald-400" : entry.avg_cohens_d > 0.5 ? "text-amber-400" : "text-slate-400"}`}>
                    {formatD(entry.avg_cohens_d)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /><span>Frontier</span></div>
          <div className="flex items-center gap-1.5"><Target className="w-3 h-3 text-amber-400" /><span>Knee Point</span></div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" /><span>Dominated</span></div>
          <div className="flex items-center gap-1.5"><span className="px-1.5 py-0.5 text-[10px] bg-slate-800 text-slate-300 rounded font-mono">BASELINE</span><span>Baseline</span></div>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>Composite = Pareto×{Math.round(data.weight_pareto * 100)}% + Significance×{Math.round(data.weight_significance * 100)}%. Higher is better.</span>
        </div>
      </div>
    </div>
  );
};