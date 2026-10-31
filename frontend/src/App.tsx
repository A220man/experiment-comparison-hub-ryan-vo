import React, { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, ChevronRight, Cpu, Download, Eye, FileCode, FileSpreadsheet, FileText, GitCompare, Layers, Plus, RefreshCw, Search, Sparkles, Tag, Trash2, Upload, X } from "lucide-react";
import { api } from "./api/client";
import { ArtifactRegistry } from "./components/ArtifactRegistry";
import { CrossSeedCard } from "./components/CrossSeedCard";
import { Leaderboard } from "./components/Leaderboard";
import { Navbar } from "./components/Navbar";
import { ParetoChart } from "./components/ParetoChart";
import { RunDiffModal } from "./components/RunDiffModal";
import { TuningRecommendations } from "./components/TuningRecommendations";
import { useAuth } from "./context/AuthContext";
import { AdvisoryExplanationResult, Artifact, AuditLogItem, CrossSeedResult, Experiment, LeaderboardResult, ParetoFrontierResult, Run, SensitivityResult, TuningRecommendationsResponse } from "./types";

const bB = "px-2.5 py-1 rounded text-xs flex items-center gap-1", bP = `${bB} bg-blue-600 hover:bg-blue-500 text-white`, bS = `${bB} bg-slate-800 hover:bg-slate-700 text-slate-300`, bI = "p-1 text-slate-400 hover:text-white";
const card = "bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl", sel = "bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-white", box = "bg-slate-950/60 p-2 rounded border border-slate-800 font-mono text-[11px]";
const td = "p-2", tdM = "p-2 font-mono text-[11px]", fB = "flex justify-between items-center", fC = "flex items-center gap-2", emp = "text-center py-4 text-xs text-slate-500", cI = "w-3.5 h-3.5", fmtO = (o: any, d = 0) => Object.entries(o || {}).map(([k, v]) => `${k}:${typeof v === "number" && d ? v.toFixed(d) : v}`).join(" ");
const inCls = "w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white", tBg = "px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 text-[10px] font-mono";

const M = ({ title, onClose, children, maxW = "max-w-md" }: any) => (
<div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75"><div className={`bg-slate-900 border border-slate-800 rounded-xl ${maxW} w-full p-4 space-y-3 shadow-2xl`}><div className={fB}><h3 className="text-sm font-bold text-white">{title}</h3><button onClick={onClose} className={bI}><X className="w-4 h-4" /></button></div>{children}</div></div>
);
const Fld = ({ l, v, set, t = "text", r, ph }: any) => (
<div><label className="block text-slate-300 text-xs mb-1">{l}</label><input type={t} required={r} placeholder={ph} value={v} onChange={e => set(t === "number" ? Number(e.target.value) : e.target.value)} className={inCls} /></div>
);
const MF = ({ onCancel, txt = "Save", dis }: any) => <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={onCancel} className={bS}>Cancel</button><button type="submit" disabled={dis} className={bP}>{txt}</button></div>;

export const App: React.FC = () => {
const { isAdmin, isAnalyst } = useAuth();
const [experiments, setExps] = useState<Experiment[]>([]), [selectedExp, setSelExp] = useState<Experiment | null>(null), [loadingExp, setLoadingExp] = useState(false), [expSearch, setExpSearch] = useState("");
const [expM, setExpM] = useState(false), [impM, setImpM] = useState(false), [importJson, setImportJson] = useState("");
const [newExp, setNewExp] = useState({ name: "", desc: "", domain: "ai-ml", baseline: "baseline" }), [tab, setTab] = useState<"runs" | "pareto" | "cross_seed" | "sensitivity" | "artifacts" | "leaderboard" | "tuning">("runs");
const [runs, setRuns] = useState<Run[]>([]), [loadingRuns, setLoadingRuns] = useState(false), [vf, setVf] = useState(""), [selDiff, setSelDiff] = useState<string[]>([]);
const [diffPair, setDiffPair] = useState<{ base: string; target: string } | null>(null), [runM, setRunM] = useState(false), [detailRun, setDetailRun] = useState<Run | null>(null);
const [newRun, setNewRun] = useState({ name: "", variant: "variant_a", seed: 42, metrics: '{"accuracy":0.88,"latency_ms":12.4}', hp: '{"lr":0.001}' });
const [isAnnotating, setIsAnnotating] = useState(false), [annotTags, setAnnotTags] = useState(""), [annotNotes, setAnnotNotes] = useState(""), [savingAnnot, setSavingAnnot] = useState(false);
const [cfg, setCfg] = useState({ m1: "accuracy", d1: "maximize" as const, m2: "latency_ms", d2: "minimize" as const, sens: "accuracy", agg: false });
const [an, setAn] = useState<{ p?: ParetoFrontierResult; cs?: CrossSeedResult; s?: SensitivityResult; adv?: AdvisoryExplanationResult; lb?: LeaderboardResult; tuning?: TuningRecommendationsResponse }>({});
const [loadingAn, setLoadingAn] = useState(false), [anErr, setAnErr] = useState<string | null>(null);
const [artifacts, setArtifacts] = useState<Artifact[]>([]), [selRunArt, setSelRunArt] = useState<string | undefined>(), [audM, setAudM] = useState(false), [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]), [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
const okM = (t: string) => setMsg({ type: "success", text: t }), erM = (e: any, p = "") => setMsg({ type: "error", text: p ? `${p}: ${e.message || e}` : (e.message || String(e)) }), clrD = () => { setDetailRun(null); setIsAnnotating(false); };
const uE = (k: string) => (v: any) => setNewExp(p => ({ ...p, [k]: v })), uR = (k: string) => (v: any) => setNewRun(p => ({ ...p, [k]: v }));
const metrics = Array.from(new Set(runs.flatMap(r => Object.keys(r.metrics || {})))), variants = Array.from(new Set(runs.map(r => r.variant_name).filter(Boolean)));
const mOpts = metrics.map(x => <option key={x} value={x}>{x}</option>), vOpts = variants.map(v => <option key={v} value={v}>{v}</option>);

const fetchExps = async () => {
setLoadingExp(true);
try { const res = await api.experiments.list(1, 50, expSearch); setExps(res.items); setSelExp(p => !p ? (res.items[0] || null) : (res.items.find(e => e.id === p.id) || res.items[0] || null)); }
catch (e: any) { erM(e, "Failed to load"); }
finally { setLoadingExp(false); }
};
useEffect(() => { fetchExps(); }, [expSearch]);

const fetchRuns = async (id: string, filter = vf) => {
setLoadingRuns(true);
try { setRuns((await api.runs.list(id, 1, 100, filter || undefined)).items); setSelDiff([]); }
catch (e: any) { erM(e, "Failed to load runs"); }
finally { setLoadingRuns(false); }
};
const fetchArts = async (id?: string) => {
const t = id || runs[0]?.id; if (!t) { setArtifacts([]); return; }
try { setArtifacts(await api.artifacts.list(t)); } catch { setArtifacts([]); }
};

useEffect(() => { if (selectedExp) { setVf(""); fetchRuns(selectedExp.id, ""); setAn({}); } }, [selectedExp?.id]);
useEffect(() => { if (metrics.length) setCfg(c => ({ ...c, m1: metrics.includes(c.m1) ? c.m1 : metrics[0], m2: metrics.includes(c.m2) ? c.m2 : metrics[1] || metrics[0], sens: metrics.includes(c.sens) ? c.sens : metrics[0] })); }, [runs.length]);
useEffect(() => {
if (tab === "artifacts") fetchArts(selRunArt || runs[0]?.id);
else if (tab === "pareto" && selectedExp && runs.length && !an.p) runPareto();
else if (tab === "cross_seed" && selectedExp && runs.length && !an.cs) runCrossSeed();
else if (tab === "sensitivity" && selectedExp && runs.length && !an.s) runSens();
else if (tab === "leaderboard" && selectedExp && runs.length && !an.lb) runLb();
else if (tab === "tuning" && selectedExp && runs.length && !an.tuning) runTuning();
}, [tab, selectedExp?.id, runs.length]);

const doAnalysis = async (fn: () => Promise<void>) => { if (!selectedExp) return; setLoadingAn(true); setAnErr(null); try { await fn(); } catch (e: any) { setAnErr(e.message); } finally { setLoadingAn(false); } };
const objs = () => [{ metric: cfg.m1 || metrics[0] || "accuracy", direction: cfg.d1 }, { metric: cfg.m2 || metrics[1] || metrics[0] || "latency_ms", direction: cfg.d2 }];
const runPareto = () => doAnalysis(async () => { const p = await api.analysis.pareto(selectedExp!.id, objs(), { aggregate_by_variant: cfg.agg, aggregation_method: "mean" }); setAn(a => ({ ...a, p })); });
const runCrossSeed = () => doAnalysis(async () => { const cs = await api.analysis.crossSeed(selectedExp!.id, metrics.length ? metrics : ["accuracy", "latency_ms"], selectedExp!.baseline_variant || undefined); setAn(a => ({ ...a, cs })); });
const runSens = (target = cfg.sens) => doAnalysis(async () => { const s = await api.analysis.sensitivity(selectedExp!.id, target || metrics[0] || "accuracy"); setAn(a => ({ ...a, s })); });
const runAdv = () => doAnalysis(async () => { const adv = await api.analysis.advisory(selectedExp!.id, "comprehensive"); setAn(a => ({ ...a, adv })); });
const runLb = () => doAnalysis(async () => { const lb = await api.analysis.leaderboard(selectedExp!.id, objs(), { baseline_variant: selectedExp!.baseline_variant, aggregate_by_variant: cfg.agg, aggregation_method: "mean", weight_pareto: 0.5, weight_significance: 0.5 }); setAn(a => ({ ...a, lb })); });
const runTuning = (target = cfg.sens) => doAnalysis(async () => { 
  const objectives = objs(); 
  const tuning = await api.tuning.recommendations(
    selectedExp!.id, 
    target || metrics[0] || "accuracy", 
    objectives.length >= 2 ? objectives : undefined,
    undefined,
    undefined,
    cfg.agg,
    "mean"
  ); 
  setAn(a => ({ ...a, tuning })); 
});

const handleCreateExp = async (e: React.FormEvent) => { e.preventDefault(); try { const exp = await api.experiments.create({ name: newExp.name, description: newExp.desc, domain: newExp.domain, baseline_variant: newExp.baseline }); setExpM(false); okM(`Created '${exp.name}'`); await fetchExps(); setSelExp(exp); } catch (err: any) { erM(err, "Create failed"); } };
const handleDeleteExp = async (id: string) => { if (!confirm("Delete experiment?")) return; try { await api.experiments.delete(id); okM("Deleted"); setSelExp(null); await fetchExps(); } catch (err: any) { erM(err, "Delete failed"); } };
const handleCreateRun = async (e: React.FormEvent) => { e.preventDefault(); if (!selectedExp) return; try { await api.runs.create({ experiment_id: selectedExp.id, name: newRun.name, variant_name: newRun.variant, seed: Number(newRun.seed), metrics: JSON.parse(newRun.metrics), hyperparameters: JSON.parse(newRun.hp) }); setRunM(false); okM("Run saved"); fetchRuns(selectedExp.id); } catch (err: any) { erM(err); } };
const handleDeleteRun = async (id: string) => { if (!confirm("Delete run?")) return; try { await api.runs.delete(id); if (selectedExp) fetchRuns(selectedExp.id); } catch {} };
const handleImportBundle = async (e: React.FormEvent) => { e.preventDefault(); if (!importJson.trim()) return; setLoadingExp(true); try { const res = await api.bundles.import(JSON.parse(importJson)); setImpM(false); setImportJson(""); okM(`Imported '${res.experiment.name}' (${res.runs_imported} runs)`); await fetchExps(); setSelExp(res.experiment); } catch (err: any) { erM(err, "Import failed"); } finally { setLoadingExp(false); } };

const handleSaveAnnot = async () => { if (!detailRun) return; setSavingAnnot(true); try { const tags = annotTags.split(",").map(t => t.trim()).filter(Boolean); const updated = await api.runs.update(detailRun.id, { tags, notes: annotNotes }); setDetailRun(updated); setRuns(prev => prev.map(r => r.id === updated.id ? updated : r)); setIsAnnotating(false); okM("Run annotations updated"); } catch (err: any) { erM(err, "Failed to update annotations"); } finally { setSavingAnnot(false); } };
const toggleDiff = (id: string) => setSelDiff(p => p.includes(id) ? p.filter(x => x !== id) : p.length >= 2 ? [p[1], id] : [...p, id]);
const exportBundle = async () => { if (!selectedExp) return; try { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(await api.bundles.export(selectedExp.id), null, 2)], { type: "application/json" })); a.download = `exp_${selectedExp.id}.json`; a.click(); } catch {} };

const spinI = <RefreshCw className={`${cI} ${loadingAn ? "animate-spin" : ""}`} />, errAlert = anErr && <div className="p-3 bg-rose-950/60 border border-rose-800 rounded text-rose-300 text-xs">{anErr}</div>;
const dirSel = (k: "d1" | "d2") => <select value={cfg[k]} onChange={e => setCfg(c => ({ ...c, [k]: e.target.value as any }))} className={sel}><option value="maximize">max</option><option value="minimize">min</option></select>;
const optPanel = (onRecalc: () => void) => (
<div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs">
<div className="flex flex-wrap items-center gap-2">
<span>X:</span><select value={cfg.m1} onChange={e => setCfg(c => ({ ...c, m1: e.target.value }))} className={sel}>{mOpts}</select>{dirSel("d1")}
<span>Y:</span><select value={cfg.m2} onChange={e => setCfg(c => ({ ...c, m2: e.target.value }))} className={sel}>{mOpts}</select>{dirSel("d2")}
<button onClick={() => { setCfg(c => ({ ...c, agg: !c.agg })); onRecalc(); }} className={`px-2 py-1 rounded text-xs border font-medium ${cfg.agg ? "bg-emerald-950 border-emerald-700 text-emerald-300" : "bg-slate-800 border-slate-700 text-slate-300 hover:text-white"}`}>{cfg.agg ? "✓ Aggregated (Mean)" : "Aggregate by Variant"}</button>
</div>
<button onClick={onRecalc} disabled={loadingAn} className={bP}>{spinI}Recompute</button>
</div>
);

return (
<div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
<Navbar onOpenAuditLogs={async () => { setAudM(true); try { setAuditLogs((await api.audit.list(1, 50)).items); } catch {} }} onNavigateHome={() => setSelExp(null)} />
{msg && (
<div className={`px-4 py-2 text-xs flex justify-between border-b ${msg.type === "success" ? "bg-emerald-950/80 border-emerald-800 text-emerald-300" : "bg-rose-950/80 border-rose-800 text-rose-300"}`}>
<div className={fC}>{msg.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}<span>{msg.text}</span></div>
<button onClick={() => setMsg(null)} className={bI}><X className="w-4 h-4" /></button>
</div>
)}
<div className="flex-1 flex max-w-7xl w-full mx-auto p-4 sm:p-6 gap-6">
<aside className={`w-80 shrink-0 flex flex-col ${card}`}>
<div className={`${fB} mb-4`}><h2 className="text-sm font-bold text-white flex items-center gap-1.5"><Layers className="w-4 h-4 text-blue-400" />Experiments</h2>
{isAnalyst && <div className={fC}><button title="Import" onClick={() => setImpM(true)} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"><Upload className="w-4 h-4" /></button><button title="New" onClick={() => setExpM(true)} className="p-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"><Plus className="w-4 h-4" /></button></div>}</div>
<div className="relative mb-3"><Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" /><input type="text" placeholder="Search..." value={expSearch} onChange={e => setExpSearch(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white" /></div>
<div className="flex-1 overflow-y-auto space-y-2">
{loadingExp && <div className={emp}>Loading...</div>}
{!loadingExp && !experiments.length && <div className={emp}>No experiments.</div>}
{experiments.map(e => (
<div key={e.id} onClick={() => setSelExp(e)} className={`p-3 rounded-lg cursor-pointer border ${selectedExp?.id === e.id ? "bg-blue-950/40 border-blue-600 text-white" : "bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700"}`}>
<div className={fB}><span className="font-semibold text-xs truncate max-w-[180px]">{e.name}</span><ChevronRight className={`${cI} text-slate-500`} /></div>
<div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono"><span>{e.domain}</span><span>{e.run_count || 0} runs</span></div>
</div>
))}
</div>
</aside>

<main className="flex-1 flex flex-col min-w-0">
{!selectedExp ? (
<div className={`flex-1 flex flex-col items-center justify-center p-12 ${card} text-center text-slate-400`}><Cpu className="w-12 h-12 text-slate-600 mb-3" /><h3 className="text-base font-bold text-white mb-1">No Experiment Selected</h3><p className="text-xs">Select or create an experiment to begin.</p></div>
) : (
<div className="space-y-4">
<div className={`${card} flex justify-between items-center`}>
<div>
<div className={fC}><h2 className="text-base font-bold text-white">{selectedExp.name}</h2><span className={tBg}>{selectedExp.domain}</span>{selectedExp.baseline_variant && <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">baseline: {selectedExp.baseline_variant}</span>}</div>
{selectedExp.description && <p className="text-xs text-slate-400 mt-0.5">{selectedExp.description}</p>}
</div>
<div className="flex gap-2">
<button onClick={() => window.open(`/api/v1/export/runs.csv?experiment_id=${selectedExp.id}` + (vf ? `&variant_name=${encodeURIComponent(vf)}` : ""))} className={bS}><FileSpreadsheet className={cI} />CSV</button>
<button onClick={() => window.open(`/api/v1/export/experiments/${selectedExp.id}/report.md`)} className={bS}><FileText className={cI} />Report</button>
<button onClick={exportBundle} className={bS}><Download className={cI} />Export</button>
{isAdmin && <button onClick={() => handleDeleteExp(selectedExp.id)} className="p-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded"><Trash2 className={cI} /></button>}
</div>
</div>

<div className="flex border-b border-slate-800 gap-2">
{(["runs", "pareto", "cross_seed", "sensitivity", "leaderboard", "artifacts", "tuning"] as const).map(k => (
<button key={k} onClick={() => setTab(k)} className={`px-3 py-2 text-xs font-semibold flex items-center gap-1.5 border-b-2 ${tab === k ? "border-blue-500 text-white bg-slate-900/60" : "border-transparent text-slate-400"}`}>
{k === "runs" ? `Runs (${runs.length})` : k === "cross_seed" ? "Cross-Seed" : k[0].toUpperCase() + k.slice(1)}
</button>
))}
</div>

{tab === "runs" && (
<div className={`${card} space-y-3`}>
<div className="flex flex-wrap justify-between items-center gap-2 text-xs">
<div className="flex items-center gap-3">
<div className="flex items-center gap-1.5 text-slate-400"><span>Variant:</span><select value={vf} onChange={e => { setVf(e.target.value); fetchRuns(selectedExp.id, e.target.value); }} className={sel}><option value="">All Variants ({runs.length})</option>{vOpts}</select></div>
<div className="flex items-center gap-2 text-slate-400"><span>Diff: {selDiff.length}/2</span>{selDiff.length === 2 && <button onClick={() => setDiffPair({ base: selDiff[0], target: selDiff[1] })} className="px-2 py-0.5 bg-emerald-600 text-white rounded flex items-center gap-1"><GitCompare className="w-3 h-3" />Compare</button>}</div>
</div>
{isAnalyst && <button onClick={() => setRunM(true)} className={bP}><Plus className={cI} />Log Run</button>}
</div>
{loadingRuns ? <div className="text-center py-4 text-xs text-slate-400">Loading...</div> : !runs.length ? <div className={emp}>No runs logged.</div> : (
<div className="overflow-x-auto">
<table className="w-full text-left text-xs">
<thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800"><tr>{["Diff", "Name", "Variant", "Seed", "Tags", "Metrics", "Hyperparams"].map(h => <th key={h} className={td}>{h}</th>)}<th className={`${td} text-right`}>Actions</th></tr></thead>
<tbody className="divide-y divide-slate-800/60 font-sans">
{runs.map(r => (
<tr key={r.id} className="hover:bg-slate-800/40">
<td className={td}><input type="checkbox" checked={selDiff.includes(r.id)} onChange={() => toggleDiff(r.id)} /></td>
<td className={`${td} font-semibold text-white cursor-pointer hover:text-blue-400`} onClick={() => setDetailRun(r)}>{r.name}</td>
<td className={`${td} font-mono text-blue-400`}>{r.variant_name}</td>
<td className={`${td} font-mono text-slate-400`}>{r.seed}</td>
<td className={td}>{(r.tags || []).map(t => <span key={t} className={`mr-1 ${tBg}`}>{t}</span>)}</td>
<td className={`${tdM} text-slate-300`}>{fmtO(r.metrics, 3)}</td>
<td className={`${tdM} text-slate-400`}>{fmtO(r.hyperparameters)}</td>
<td className={`${td} text-right space-x-1`}>
<button title="Inspect" onClick={() => setDetailRun(r)} className={bI}><Eye className={cI} /></button>
<button title="Artifacts" onClick={() => { setSelRunArt(r.id); setTab("artifacts"); }} className={bI}><FileCode className={cI} /></button>
{isAnalyst && <button title="Delete" onClick={() => handleDeleteRun(r.id)} className="p-1 text-slate-500 hover:text-rose-400"><Trash2 className={cI} /></button>}
</td>
</tr>
))}
</tbody>
</table>
</div>
)}
</div>
)}

{tab === "pareto" && (<div className="space-y-3">{optPanel(runPareto)}{errAlert}{an.p ? <ParetoChart data={an.p} onSelectRun={id => { const r = runs.find(x => x.id === id); if (r) setDetailRun(r); }} /> : <div className="p-6 text-center text-slate-500 text-xs">No Pareto data.</div>}</div>)}
{tab === "cross_seed" && (<div className="space-y-3"><div className="flex justify-end"><button onClick={runCrossSeed} disabled={loadingAn} className={bP}>{spinI}Recalculate</button></div>{errAlert}{an.cs ? <CrossSeedCard data={an.cs} /> : <div className="p-6 text-center text-slate-500 text-xs">No cross-seed statistics.</div>}</div>)}
{tab === "sensitivity" && (
<div className="space-y-4">
<div className={`${card} space-y-3`}>
<div className={fB}><div><h3 className="text-sm font-semibold text-white">Hyperparameter Sensitivity</h3><p className="text-xs text-slate-400">Spearman correlation & feature importance</p></div><div className={fC}><select value={cfg.sens} onChange={e => { const v = e.target.value; setCfg(c => ({ ...c, sens: v })); runSens(v); }} className={sel}>{mOpts}</select><button onClick={() => runSens(cfg.sens)} disabled={loadingAn} className={bS}>{spinI}Refresh</button></div></div>
{an.s?.parameters.length ? (<div className="space-y-1.5">{an.s.parameters.map(p => (<div key={p.parameter} className={`flex justify-between ${box}`}><div><b className="text-white">{p.parameter}</b><span className="ml-2 text-slate-400">({p.parameter_type})</span><p className="text-[11px] text-slate-400 mt-0.5">{p.summary}</p></div><div className="text-right text-blue-400 font-bold">{(p.importance_score * 100).toFixed(1)}%</div></div>))}</div>) : <div className={emp}>No parameter variance.</div>}
</div>
<div className={`${card} space-y-3`}>
<div className={fB}><div><h3 className="text-sm font-semibold text-white flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-purple-400" />Grounded Advisory Explanation</h3><p className="text-xs text-slate-400">Trade-off synthesis</p></div><button onClick={runAdv} disabled={loadingAn} className="px-2.5 py-1 bg-purple-600 text-white rounded text-xs flex items-center gap-1"><Sparkles className={cI} />Generate</button></div>
{an.adv ? (<div className="space-y-2 text-xs"><div className="p-2.5 bg-purple-950/30 border border-purple-800 rounded text-purple-200"><b>Disclaimer: </b>{an.adv.disclaimer}</div><div className="p-3 bg-slate-950/70 border border-slate-800 rounded whitespace-pre-wrap text-slate-300">{an.adv.advisory_text}</div><div className="flex justify-between text-[11px] text-slate-500 font-mono"><span>Provider: {an.adv.provider}</span><span>Fallback: {an.adv.offline_fallback ? "Yes" : "No"}</span></div></div>) : <div className="text-center py-4 text-xs text-slate-500 border border-dashed border-slate-800 rounded">Click 'Generate' for advisory.</div>}
</div>
</div>
)}
{tab === "leaderboard" && (<div className="space-y-3">{optPanel(runLb)}{errAlert}{an.lb ? <Leaderboard data={an.lb} /> : <div className="p-6 text-center text-slate-500 text-xs">No leaderboard data.</div>}</div>)}
{tab === "artifacts" && (<ArtifactRegistry artifacts={artifacts} runId={selRunArt || runs[0]?.id} onRefresh={() => fetchArts(selRunArt || runs[0]?.id)} />)}
{tab === "tuning" && (
  <div className="space-y-3">
    <div className="flex justify-end">
      <button onClick={() => runTuning(cfg.sens)} disabled={loadingAn} className={bP}>{spinI}Refresh</button>
    </div>
    {errAlert}
    {an.tuning ? <TuningRecommendations data={an.tuning} onRefresh={runTuning} availableMetrics={metrics} /> : <div className="p-6 text-center text-slate-500 text-xs">No tuning recommendations.</div>}
  </div>
)}
</div>
)}
</main>
</div>

{expM && (<M title="New Experiment" onClose={() => setExpM(false)}><form onSubmit={handleCreateExp} className="space-y-2 text-xs"><Fld l="Name" r v={newExp.name} set={uE("name")} /><Fld l="Baseline Variant" v={newExp.baseline} set={uE("baseline")} /><Fld l="Description" v={newExp.desc} set={uE("desc")} /><MF onCancel={() => setExpM(false)} txt="Create" /></form></M>)}
{impM && (<M title="Import Experiment Bundle" onClose={() => setImpM(false)}><form onSubmit={handleImportBundle} className="space-y-3 text-xs"><textarea rows={5} value={importJson} onChange={e => setImportJson(e.target.value)} placeholder='{"format": "bundle", ...}' className={`${inCls} font-mono text-[11px] h-24`} /><MF onCancel={() => setImpM(false)} txt="Import" dis={loadingExp || !importJson.trim()} /></form></M>)}
{runM && selectedExp && (<M title="Log Run" onClose={() => setRunM(false)}><form onSubmit={handleCreateRun} className="space-y-2 text-xs"><div className="grid grid-cols-2 gap-2"><Fld l="Run Name" r v={newRun.name} set={uR("name")} /><Fld l="Variant" r v={newRun.variant} set={uR("variant")} /></div><Fld l="Seed" t="number" r v={newRun.seed} set={uR("seed")} /><Fld l="Metrics (JSON)" r v={newRun.metrics} set={uR("metrics")} /><Fld l="Hyperparams (JSON)" v={newRun.hp} set={uR("hp")} /><MF onCancel={() => setRunM(false)} /></form></M>)}

{detailRun && (<M title={`Run: ${detailRun.name}`} onClose={clrD} maxW="max-w-xl">
<div className="space-y-3 text-xs">
<div className={`grid grid-cols-2 gap-2 ${box}`}>{[["Variant", detailRun.variant_name, "text-blue-400 font-bold"], ["Seed", detailRun.seed], ["Status", detailRun.status, "text-emerald-400"], ["Commit", detailRun.commit_hash || "—"]].map(([k, v, c]) => <div key={k as string}><span className="text-slate-500">{k}: </span><span className={c as string}>{v}</span></div>)}</div>
{isAnnotating ? (
<div className="space-y-2 p-2 bg-slate-950/80 border border-slate-800 rounded">
<Fld l="Tags" v={annotTags} set={setAnnotTags} ph="comma-separated" />
<div><label className="block text-slate-300 text-xs mb-1">Notes</label><textarea value={annotNotes} onChange={e => setAnnotNotes(e.target.value)} className={inCls} rows={2} /></div>
<div className="flex justify-end gap-2"><button onClick={() => setIsAnnotating(false)} className={bS}>Cancel</button><button onClick={handleSaveAnnot} disabled={savingAnnot} className={bP}>{savingAnnot ? "Saving..." : "Save Annotations"}</button></div>
</div>
) : (
<div className="space-y-2">
{detailRun.tags && detailRun.tags.length > 0 && (<div className="flex flex-wrap gap-1 items-center"><span className="text-slate-500 text-[11px] flex items-center gap-1"><Tag className="w-3 h-3" />Tags:</span>{detailRun.tags.map(t => <span key={t} className={tBg}>{t}</span>)}</div>)}
{detailRun.notes && <p className="text-slate-400 bg-slate-950/40 p-2 rounded border border-slate-800">{detailRun.notes}</p>}
</div>
)}
<div><h4 className="font-semibold text-slate-300 mb-1 text-[11px]">Metrics</h4><div className={`grid grid-cols-2 gap-1 ${box}`}>{Object.entries(detailRun.metrics).map(([k, v]) => (<div key={k} className="flex justify-between p-1 bg-slate-900/60 rounded"><span className="text-slate-400">{k}:</span><b className="text-white">{typeof v === "number" ? v.toFixed(4) : v}</b></div>))}</div></div>
<div className="flex justify-between items-center pt-2 border-t border-slate-800">
<div>{isAnalyst && !isAnnotating && <button onClick={() => { setAnnotTags((detailRun.tags || []).join(", ")); setAnnotNotes(detailRun.notes || ""); setIsAnnotating(true); }} className={bS}><Tag className={cI} />Annotate</button>}</div>
<div className="flex gap-2"><button onClick={() => { setSelRunArt(detailRun.id); setTab("artifacts"); clrD(); }} className={bS}><FileCode className={cI} />Artifacts</button><button onClick={clrD} className={bP}>Close</button></div>
</div>
</div>
</M>)}

{diffPair && <RunDiffModal baseRunId={diffPair.base} targetRunId={diffPair.target} onClose={() => setDiffPair(null)} />}
{audM && (<M title="Security Audit Trail" onClose={() => setAudM(false)} maxW="max-w-2xl"><div className="max-h-[60vh] overflow-y-auto space-y-1 font-mono text-[11px]">{auditLogs.map(l => <div key={l.id} className={`flex justify-between ${box}`}><span className="text-blue-400">{l.user_email}</span><span className="text-white font-bold">{l.action}</span><span className="text-slate-400">{l.resource_type}:{l.resource_id}</span></div>)}</div></M>)}
</div>
);
};

export default App;
