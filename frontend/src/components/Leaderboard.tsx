import React from "react";
import { Trophy, TrendingUp, TrendingDown, BarChart2 } from "lucide-react";
import { LeaderboardResult, LeaderboardEntry } from "../types";
const card = "bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl", bBg = "bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400";
const td = "p-2", tdM = "p-2 font-mono text-[11px]", fmt = (v: number, d = 3) => v.toFixed(d);
export const Leaderboard: React.FC<{ data: LeaderboardResult | null }> = ({ data }) => {
if (!data?.leaderboard?.length) return (
<div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
<BarChart2 className="w-8 h-8 mx-auto mb-2 text-slate-500 animate-pulse" />
<p className="text-sm">No variant data available for leaderboard.</p>
<p className="text-xs text-slate-500 mt-1">Log runs with multiple variants to compute rankings.</p>
</div>
);
const { objectives, leaderboard, is_aggregated, aggregation_method, weight_pareto, weight_significance, total_variants } = data;
return (
<div className={card}>
<div className="flex flex-wrap items-center justify-between gap-4 mb-4">
<div>
<h3 className="text-sm font-semibold text-white flex items-center gap-2">
Variant Leaderboard
<span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
{is_aggregated ? `Aggregated (${aggregation_method || "mean"})` : "Raw"}
</span>
</h3>
<p className="text-xs text-slate-400 mt-0.5">Objectives: <b className="text-slate-200">{objectives.map(o => `${o.metric} (${o.direction})`).join(" vs ")}</b></p>
</div>
<div className="flex items-center gap-3 text-xs">
<div className={bBg}>Pareto <b className="font-mono text-blue-400">{Math.round(weight_pareto * 100)}%</b> / Sig <b className="font-mono text-amber-400">{Math.round(weight_significance * 100)}%</b></div>
<div className={bBg}>Variants: <b className="font-mono text-emerald-400">{total_variants}</b></div>
</div>
</div>
<div className="overflow-x-auto">
<table className="w-full text-left text-xs">
<thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800 sticky top-0">
<tr>
{["Rank", "Variant"].map(h => <th key={h} className={td}>{h}</th>)}{["Composite", "Pareto", "Significance", "Frontier", "Knee"].map(h => <th key={h} className={tdM}>{h}</th>)}
{objectives.map((o, i) => <th key={i} className={tdM}>{o.metric}</th>)}
{["N (seeds)", "p-value", "Cohen's d"].map(h => <th key={h} className={tdM}>{h}</th>)}
</tr>
</thead>
<tbody className="divide-y divide-slate-800/60 font-sans">
{leaderboard.map((e: LeaderboardEntry) => (
<tr key={e.variant_name} className={`hover:bg-slate-800/40 ${e.is_baseline ? "bg-slate-950/50" : ""}`}>
<td className={td}>
<span className={`font-bold ${e.rank === 1 ? "text-amber-400" : e.rank === 2 ? "text-slate-300" : e.rank === 3 ? "text-amber-600" : "text-slate-400"}`}>
#{e.rank}
{e.rank === 1 && <Trophy className="w-3.5 h-3.5 inline ml-1 text-amber-400" />}
{e.rank === 2 && <TrendingUp className="w-3.5 h-3.5 inline ml-1 text-slate-300" />}
{e.rank === 3 && <TrendingDown className="w-3.5 h-3.5 inline ml-1 text-amber-600" />}
</span>
</td>
<td className={`${td} font-semibold text-white`}>
{e.is_baseline && <span className="mr-1.5 px-1.5 py-0.5 text-[10px] bg-slate-800 text-slate-300 rounded font-mono">BASELINE</span>}
{e.variant_name}
</td>
<td className={tdM}><b className={`font-mono ${e.composite_score >= 0.7 ? "text-emerald-400" : e.composite_score >= 0.4 ? "text-amber-400" : "text-rose-400"}`}>{fmt(e.composite_score)}</b></td>
<td className={tdM}><span className="font-mono text-blue-400">{fmt(e.pareto_score)}</span></td>
<td className={tdM}><span className="font-mono text-amber-400">{fmt(e.significance_score)}</span></td>
<td className={tdM}>{e.is_frontier ? <span className="text-emerald-400 font-bold">● Frontier</span> : <span className="text-slate-500">○ Dominated</span>}</td>
<td className={tdM}>{e.is_knee_point ? <span className="px-1.5 py-0.5 rounded bg-blue-950 border border-blue-700 text-blue-300 font-bold text-[10px]">★ KNEE</span> : <span className="text-slate-600">—</span>}</td>
{objectives.map((o, i) => <td key={i} className={tdM}>{fmt(e.metrics[o.metric] ?? 0, 4)}</td>)}
<td className={tdM}><span className="font-mono text-slate-300">{e.sample_size_n}</span> <span className="text-slate-500 text-[10px]">({e.seeds.join(",")})</span></td>
<td className={tdM}><span className={`font-mono ${e.avg_welch_p_value < 0.05 ? "text-emerald-400 font-bold" : "text-slate-400"}`}>{e.avg_welch_p_value < 0.001 ? "< 0.001" : fmt(e.avg_welch_p_value, 4)}</span></td>
<td className={tdM}><span className={`font-mono ${e.avg_cohens_d >= 0.8 ? "text-emerald-400 font-bold" : e.avg_cohens_d >= 0.5 ? "text-amber-400" : "text-slate-400"}`}>{fmt(e.avg_cohens_d, 2)}</span></td>
</tr>
))}
</tbody>
</table>
</div>
</div>
);
};
