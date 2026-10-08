import React, { useEffect, useState } from "react";
import { AlertCircle, BarChart2, CheckCircle2, ChevronRight, Cpu, Download, Eye, FileCode, FileSpreadsheet, FileText, GitCompare, Layers, Plus, RefreshCw, Search, Sparkles, Trash2, Upload, X } from "lucide-react";
import { api } from "./api/client";
import { ArtifactRegistry } from "./components/ArtifactRegistry";
import { CrossSeedCard } from "./components/CrossSeedCard";
import { Navbar } from "./components/Navbar";
import { ParetoChart } from "./components/ParetoChart";
import { RunDiffModal } from "./components/RunDiffModal";
import { useAuth } from "./context/AuthContext";
import { AdvisoryExplanationResult, Artifact, AuditLogItem, CrossSeedResult, Experiment, ParetoFrontierResult, Run, SensitivityResult } from "./types";

const bB = "px-2.5 py-1 rounded text-xs flex items-center gap-1", bPri = `${bB} bg-blue-600 hover:bg-blue-500 text-white`, bSec = `${bB} bg-slate-800 hover:bg-slate-700 text-slate-300`, bI = "p-1 text-slate-400 hover:text-white";
const card = "bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl", sel = "bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-white", box = "bg-slate-950/60 p-2 rounded border border-slate-800 font-mono text-[11px]";
const td = "p-2", tdM = "p-2 font-mono text-[11px]";

const M: React.FC<{ title: string; onClose: () => void; children: React.ReactNode; maxW?: string }> = ({ title, onClose, children, maxW = "max-w-md" }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75">
    <div className={`bg-slate-900 border border-slate-800 rounded-xl ${maxW} w-full p-4 space-y-3 shadow-2xl`}>
      <div className="flex justify-between items-center"><h3 className="text-sm font-bold text-white">{title}</h3><button onClick={onClose} className={bI}><X className="w-4 h-4" /></button></div>
      {children}
    </div>
  </div>
);

const Inp: React.FC<{ label: string; [k: string]: any }> = ({ label, ...p }) => (
  <div><label className="block text-slate-300 text-xs mb-1">{label}</label><input className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white" {...p} /></div>
);
const MF = ({ onCancel, txt = "Save", dis }: any) => <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={onCancel} className={bSec}>Cancel</button><button type="submit" disabled={dis} className={bPri}>{txt}</button></div>;

export const App: React.FC = () => {
  const { isAdmin, isAnalyst } = useAuth();
  const [experiments, setExperiments] = useState<Experiment[]>([]), [selectedExp, setSelectedExp] = useState<Experiment | null>(null), [loadingExp, setLoadingExp] = useState(false), [expSearch, setExpSearch] = useState("");
  const [showExpModal, setShowExpModal] = useState(false), [showImportModal, setShowImportModal] = useState(false), [importJson, setImportJson] = useState(""), [importing, setImporting] = useState(false);
  const [newExp, setNewExp] = useState({ name: "", desc: "", domain: "ai-ml", baseline: "baseline" }), [tab, setTab] = useState<"runs" | "pareto" | "cross_seed" | "sensitivity" | "artifacts">("runs");

  const [runs, setRuns] = useState<Run[]>([]), [loadingRuns, setLoadingRuns] = useState(false), [variantFilter, setVariantFilter] = useState(""), [selDiff, setSelDiff] = useState<string[]>([]);
  const [diffPair, setDiffPair] = useState<{ base: string; target: string } | null>(null), [showRunModal, setShowRunModal] = useState(false), [selectedRunDetail, setSelectedRunDetail] = useState<Run | null>(null);
  const [newRun, setNewRun] = useState({ name: "", variant: "variant_a", seed: 42, metrics: '{"accuracy": 0.88, "latency_ms": 12.4}', hp: '{"lr": 0.001}' });
  const setE = (k: string, v: string) => setNewExp(p => ({ ...p, [k]: v })), setR = (k: string, v: any) => setNewRun(p => ({ ...p, [k]: v }));
  const bindE = (k: string) => ({ value: (newExp as any)[k], onChange: (e: any) => setE(k, e.target.value) });
  const bindR = (k: string) => ({ value: (newRun as any)[k], onChange: (e: any) => setR(k, e.target.value) });

  const [obj1Metric, setObj1Metric] = useState("accuracy"), [obj1Dir, setObj1Dir] = useState<"maximize" | "minimize">("maximize");
  const [obj2Metric, setObj2Metric] = useState("latency_ms"), [obj2Dir, setObj2Dir] = useState<"maximize" | "minimize">("minimize"), [sensMetric, setSensMetric] = useState("accuracy");

  const [paretoData, setParetoData] = useState<ParetoFrontierResult | null>(null), [crossSeedData, setCrossSeedData] = useState<CrossSeedResult | null>(null), [sensitivityData, setSensitivityData] = useState<SensitivityResult | null>(null), [advisoryData, setAdvisoryData] = useState<AdvisoryExplanationResult | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false), [analysisError, setAnalysisError] = useState<string | null>(null);

  const [artifacts, setArtifacts] = useState<Artifact[]>([]), [selectedRunArtifacts, setSelectedRunArtifacts] = useState<string | undefined>(), [showAuditModal, setShowAuditModal] = useState(false), [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]), [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const availableMetrics = Array.from(new Set(runs.flatMap(r => Object.keys(r.metrics || {})))), availableVariants = Array.from(new Set(runs.map(r => r.variant_name).filter(Boolean)));
  const metricOpts = availableMetrics.map(x => <option key={x} value={x}>{x}</option>), variantOpts = availableVariants.map(v => <option key={v} value={v}>{v}</option>);

  const fetchExperiments = async () => {
    setLoadingExp(true);
    try {
      const res = await api.experiments.list(1, 50, expSearch);
      setExperiments(res.items);
      if (res.items.length && !selectedExp) setSelectedExp(res.items[0]);
      else if (selectedExp) setSelectedExp(res.items.find(e => e.id === selectedExp.id) || res.items[0] || null);
    } catch (e: any) { setMsg({ type: "error", text: e.message || "Failed to load" }); }
    finally { setLoadingExp(false); }
  };

  useEffect(() => { fetchExperiments(); }, [expSearch]);

  const fetchRuns = async (id: string, vf = variantFilter) => {
    setLoadingRuns(true);
    try { setRuns((await api.runs.list(id, 1, 100, vf || undefined)).items); setSelDiff([]); }
    catch (e: any) { setMsg({ type: "error", text: e.message || "Failed to load runs" }); }
    finally { setLoadingRuns(false); }
  };

  const fetchArtifacts = async (id?: string) => {
    const target = id || runs[0]?.id;
    if (!target) { setArtifacts([]); return; }
    try { setArtifacts(await api.artifacts.list(target)); } catch { setArtifacts([]); }
  };

  useEffect(() => {
    if (selectedExp) {
      setVariantFilter(""); fetchRuns(selectedExp.id, "");
      setParetoData(null); setCrossSeedData(null); setSensitivityData(null); setAdvisoryData(null);
    }
  }, [selectedExp?.id]);

  useEffect(() => {
    if (availableMetrics.length) {
      if (!availableMetrics.includes(obj1Metric)) setObj1Metric(availableMetrics[0]);
      if (!availableMetrics.includes(obj2Metric)) setObj2Metric(availableMetrics[1] || availableMetrics[0]);
      if (!availableMetrics.includes(sensMetric)) setSensMetric(availableMetrics[0]);
    }
  }, [runs.length]);

  useEffect(() => {
    if (tab === "artifacts") fetchArtifacts(selectedRunArtifacts || runs[0]?.id);
    else if (tab === "pareto" && selectedExp && runs.length && !paretoData) runPareto();
    else if (tab === "cross_seed" && selectedExp && runs.length && !crossSeedData) runCrossSeed();
    else if (tab === "sensitivity" && selectedExp && runs.length && !sensitivityData) runSensitivity();
  }, [tab, selectedExp?.id, runs.length]);

  const handleCreateExp = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const exp = await api.experiments.create({ name: newExp.name, description: newExp.desc, domain: newExp.domain, baseline_variant: newExp.baseline });
      setShowExpModal(false); setMsg({ type: "success", text: `Created '${exp.name}'` });
      await fetchExperiments(); setSelectedExp(exp);
    } catch (err: any) { setMsg({ type: "error", text: err.message || "Create failed" }); }
  };

  const handleDeleteExp = async (id: string) => {
    if (!confirm("Delete experiment?")) return;
    try { await api.experiments.delete(id); setMsg({ type: "success", text: "Deleted" }); setSelectedExp(null); await fetchExperiments(); }
    catch (err: any) { setMsg({ type: "error", text: err.message || "Delete failed" }); }
  };

  const handleCreateRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedExp) return;
    try {
      await api.runs.create({ experiment_id: selectedExp.id, name: newRun.name, variant_name: newRun.variant, seed: Number(newRun.seed), metrics: JSON.parse(newRun.metrics), hyperparameters: JSON.parse(newRun.hp) });
      setShowRunModal(false); setMsg({ type: "success", text: "Run saved" }); fetchRuns(selectedExp.id);
    } catch (err: any) { setMsg({ type: "error", text: err.message || "Failed" }); }
  };
  const handleDeleteRun = async (id: string) => {
    if (!confirm("Delete run?")) return;
    try { await api.runs.delete(id); if (selectedExp) fetchRuns(selectedExp.id); } catch {}
  };

  const handleImportBundle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importJson.trim()) return;
    setImporting(true);
    try {
      const res = await api.bundles.import(JSON.parse(importJson));
      setShowImportModal(false); setImportJson(""); setMsg({ type: "success", text: `Imported '${res.experiment.name}' (${res.runs_imported} runs)` });
      await fetchExperiments(); setSelectedExp(res.experiment);
    } catch (err: any) { setMsg({ type: "error", text: err.message || "Import failed" }); }
    finally { setImporting(false); }
  };

  const toggleDiff = (id: string) => setSelDiff(p => p.includes(id) ? p.filter(x => x !== id) : p.length >= 2 ? [p[1], id] : [...p, id]);

  const doAnalysis = async (fn: () => Promise<void>) => {
    if (!selectedExp) return;
    setLoadingAnalysis(true); setAnalysisError(null);
    try { await fn(); } catch (e: any) { setAnalysisError(e.message); }
    finally { setLoadingAnalysis(false); }
  };

  const runPareto = (m1 = obj1Metric, d1 = obj1Dir, m2 = obj2Metric, d2 = obj2Dir) => {
    const p1 = m1 || availableMetrics[0] || "accuracy", p2 = m2 || availableMetrics[1] || availableMetrics[0] || "latency_ms";
    doAnalysis(async () => setParetoData(await api.analysis.pareto(selectedExp!.id, [{ metric: p1, direction: d1 }, { metric: p2, direction: d2 }])));
  };

  const runCrossSeed = () => doAnalysis(async () => setCrossSeedData(await api.analysis.crossSeed(selectedExp!.id, availableMetrics.length ? availableMetrics : ["accuracy", "latency_ms"], selectedExp!.baseline_variant || undefined)));
  const runSensitivity = (target = sensMetric) => doAnalysis(async () => setSensitivityData(await api.analysis.sensitivity(selectedExp!.id, target || availableMetrics[0] || "accuracy")));
  const runAdvisory = () => doAnalysis(async () => setAdvisoryData(await api.analysis.advisory(selectedExp!.id, "comprehensive")));

  const exportBundle = async () => {
    if (!selectedExp) return;
    try {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(await api.bundles.export(selectedExp.id), null, 2)], { type: "application/json" }));
      a.download = `exp_${selectedExp.id}.json`; a.click();
    } catch {}
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar onOpenAuditLogs={async () => { setShowAuditModal(true); try { setAuditLogs((await api.audit.list(1, 50)).items); } catch {} }} onNavigateHome={() => setSelectedExp(null)} />
      {msg && (
        <div className={`px-4 py-2 text-xs flex justify-between border-b ${msg.type === "success" ? "bg-emerald-950/80 border-emerald-800 text-emerald-300" : "bg-rose-950/80 border-rose-800 text-rose-300"}`}>
          <div className="flex items-center gap-2">{msg.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}<span>{msg.text}</span></div>
          <button onClick={() => setMsg(null)} className={bI}><X className="w-4 h-4" /></button>
        </div>
      )}
      <div className="flex-1 flex max-w-7xl w-full mx-auto p-4 sm:p-6 gap-6">
        <aside className="w-80 shrink-0 flex flex-col bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-1.5"><Layers className="w-4 h-4 text-blue-400" />Experiments</h2>
            {isAnalyst && (
              <div className="flex items-center gap-1.5">
                <button title="Import Bundle" onClick={() => setShowImportModal(true)} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"><Upload className="w-4 h-4" /></button>
                <button title="New Experiment" onClick={() => setShowExpModal(true)} className="p-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"><Plus className="w-4 h-4" /></button>
              </div>
            )}
          </div>
          <div className="relative mb-3">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input type="text" placeholder="Search..." value={expSearch} onChange={e => setExpSearch(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white" />
          </div>
          <div className="flex-1 overflow-y-auto space-y-2">
            {loadingExp && <div className="text-center py-6 text-xs text-slate-500">Loading...</div>}
            {!loadingExp && !experiments.length && <div className="text-center py-8 text-xs text-slate-500">No experiments.</div>}
            {experiments.map(e => (
              <div key={e.id} onClick={() => setSelectedExp(e)} className={`p-3 rounded-lg cursor-pointer border ${selectedExp?.id === e.id ? "bg-blue-950/40 border-blue-600 text-white" : "bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700"}`}>
                <div className="flex justify-between"><span className="font-semibold text-xs truncate max-w-[180px]">{e.name}</span><ChevronRight className="w-3.5 h-3.5 text-slate-500" /></div>
                <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono"><span>{e.domain}</span><span>{e.run_count || 0} runs</span></div>
              </div>
            ))}
          </div>
        </aside>

        <main className="flex-1 flex flex-col min-w-0">
          {!selectedExp ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl text-center text-slate-400">
              <Cpu className="w-12 h-12 text-slate-600 mb-3" /><h3 className="text-base font-bold text-white mb-1">No Experiment Selected</h3><p className="text-xs">Select or create an experiment to begin.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className={`${card} flex justify-between items-center`}>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-white">{selectedExp.name}</h2>
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono">{selectedExp.domain}</span>
                    {selectedExp.baseline_variant && <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">baseline: {selectedExp.baseline_variant}</span>}
                  </div>
                  {selectedExp.description && <p className="text-xs text-slate-400 mt-0.5">{selectedExp.description}</p>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => window.open(`/api/v1/export/runs.csv?experiment_id=${selectedExp.id}${variantFilter ? `&variant_name=${encodeURIComponent(variantFilter)}` : ""}`)} className={bSec}><FileSpreadsheet className="w-3.5 h-3.5" />CSV</button>
                  <button onClick={() => window.open(`/api/v1/export/experiments/${selectedExp.id}/report.md`)} className={bSec}><FileText className="w-3.5 h-3.5" />Report</button>
                  <button onClick={exportBundle} className={bSec}><Download className="w-3.5 h-3.5" />Export</button>
                  {isAdmin && <button onClick={() => handleDeleteExp(selectedExp.id)} className="p-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded"><Trash2 className="w-3.5 h-3.5" /></button>}
                </div>
              </div>

              <div className="flex border-b border-slate-800 gap-2">
                {([["runs", `Runs (${runs.length})`, Layers], ["pareto", "Pareto", BarChart2], ["cross_seed", "Cross-Seed", GitCompare], ["sensitivity", "Sensitivity", Sparkles], ["artifacts", "Artifacts", FileCode]] as const).map(([k, l, I]) => (
                  <button key={k} onClick={() => setTab(k as any)} className={`px-3 py-2 text-xs font-semibold flex items-center gap-1.5 border-b-2 ${tab === k ? "border-blue-500 text-white bg-slate-900/60" : "border-transparent text-slate-400"}`}><I className="w-3.5 h-3.5" />{l}</button>
                ))}
              </div>

              {tab === "runs" && (
                <div className={`${card} space-y-3`}>
                  <div className="flex flex-wrap justify-between items-center gap-2 text-xs">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 text-slate-400">
                        <span>Variant:</span>
                        <select value={variantFilter} onChange={e => { setVariantFilter(e.target.value); fetchRuns(selectedExp.id, e.target.value); }} className={sel}>
                          <option value="">All Variants ({runs.length})</option>
                          {variantOpts}
                        </select>
                      </div>
                      <div className="flex items-center gap-2 text-slate-400">
                        <span>Diff: {selDiff.length}/2</span>
                        {selDiff.length === 2 && <button onClick={() => setDiffPair({ base: selDiff[0], target: selDiff[1] })} className="px-2 py-0.5 bg-emerald-600 text-white rounded flex items-center gap-1"><GitCompare className="w-3 h-3" />Compare</button>}
                      </div>
                    </div>
                    {isAnalyst && <button onClick={() => setShowRunModal(true)} className={bPri}><Plus className="w-3.5 h-3.5" />Log Run</button>}
                  </div>
                  {loadingRuns ? <div className="text-center py-4 text-xs text-slate-400">Loading...</div> : !runs.length ? <div className="text-center py-4 text-xs text-slate-500">No runs logged.</div> : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                          <tr>{["Diff", "Name", "Variant", "Seed", "Metrics", "Hyperparams"].map(h => <th key={h} className={td}>{h}</th>)}<th className={`${td} text-right`}>Actions</th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-sans">
                          {runs.map(r => (
                            <tr key={r.id} className="hover:bg-slate-800/40">
                              <td className={td}><input type="checkbox" checked={selDiff.includes(r.id)} onChange={() => toggleDiff(r.id)} /></td>
                              <td className={`${td} font-semibold text-white cursor-pointer hover:text-blue-400`} onClick={() => setSelectedRunDetail(r)}>{r.name}</td>
                              <td className={`${td} font-mono text-blue-400`}>{r.variant_name}</td>
                              <td className={`${td} font-mono text-slate-400`}>{r.seed}</td>
                              <td className={`${tdM} text-slate-300`}>{Object.entries(r.metrics).map(([k, v]) => `${k}:${Number(v).toFixed(3)}`).join(" ")}</td>
                              <td className={`${tdM} text-slate-400`}>{Object.entries(r.hyperparameters).map(([k, v]) => `${k}:${v}`).join(", ")}</td>
                              <td className={`${td} text-right space-x-1`}>
                                <button title="Inspect Run" onClick={() => setSelectedRunDetail(r)} className={bI}><Eye className="w-3.5 h-3.5" /></button>
                                <button title="Artifacts" onClick={() => { setSelectedRunArtifacts(r.id); setTab("artifacts"); }} className={bI}><FileCode className="w-3.5 h-3.5" /></button>
                                {isAnalyst && <button title="Delete Run" onClick={() => handleDeleteRun(r.id)} className="p-1 text-slate-500 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {(tab === "pareto" || tab === "cross_seed") && (
                <div className="space-y-3">
                  {tab === "pareto" ? (
                    <div className="flex items-center justify-between p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs">
                      <div className="flex items-center gap-2">
                        <span>X:</span><select value={obj1Metric} onChange={e => setObj1Metric(e.target.value)} className={sel}>{metricOpts}</select>
                        <select value={obj1Dir} onChange={e => setObj1Dir(e.target.value as any)} className={sel}><option value="maximize">max</option><option value="minimize">min</option></select>
                        <span>Y:</span><select value={obj2Metric} onChange={e => setObj2Metric(e.target.value)} className={sel}>{metricOpts}</select>
                        <select value={obj2Dir} onChange={e => setObj2Dir(e.target.value as any)} className={sel}><option value="minimize">min</option><option value="maximize">max</option></select>
                      </div>
                      <button onClick={() => runPareto()} disabled={loadingAnalysis} className={bPri}><RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? "animate-spin" : ""}`} />Recompute</button>
                    </div>
                  ) : (
                    <div className="flex justify-end"><button onClick={runCrossSeed} disabled={loadingAnalysis} className={bPri}><RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? "animate-spin" : ""}`} />Recalculate</button></div>
                  )}
                  {analysisError && <div className="p-3 bg-rose-950/60 border border-rose-800 rounded text-rose-300 text-xs">{analysisError}</div>}
                  {tab === "pareto" ? (paretoData ? <ParetoChart data={paretoData} onSelectRun={id => { const r = runs.find(x => x.id === id); if (r) setSelectedRunDetail(r); }} /> : <div className="p-6 text-center text-slate-500 text-xs">No Pareto data.</div>) : (crossSeedData ? <CrossSeedCard data={crossSeedData} /> : <div className="p-6 text-center text-slate-500 text-xs">No cross-seed statistics.</div>)}
                </div>
              )}

              {tab === "sensitivity" && (
                <div className="space-y-4">
                  <div className={`${card} space-y-3`}>
                    <div className="flex justify-between items-center">
                      <div><h3 className="text-sm font-semibold text-white">Hyperparameter Sensitivity</h3><p className="text-xs text-slate-400">Spearman correlation & feature importance</p></div>
                      <div className="flex items-center gap-2">
                        <select value={sensMetric} onChange={e => { setSensMetric(e.target.value); runSensitivity(e.target.value); }} className={sel}>{metricOpts}</select>
                        <button onClick={() => runSensitivity(sensMetric)} disabled={loadingAnalysis} className={bSec}><RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? "animate-spin" : ""}`} />Refresh</button>
                      </div>
                    </div>
                    {sensitivityData?.parameters.length ? (
                      <div className="space-y-1.5">
                        {sensitivityData.parameters.map(p => (
                          <div key={p.parameter} className={`flex justify-between ${box}`}>
                            <div><span className="font-bold text-white">{p.parameter}</span><span className="ml-2 text-slate-400">({p.parameter_type})</span><p className="text-[11px] text-slate-400 mt-0.5">{p.summary}</p></div>
                            <div className="text-right text-blue-400 font-bold">{(p.importance_score * 100).toFixed(1)}%</div>
                          </div>
                        ))}
                      </div>
                    ) : <div className="text-center py-4 text-xs text-slate-500">No parameter variance.</div>}
                  </div>

                  <div className={`${card} space-y-3`}>
                    <div className="flex justify-between items-center">
                      <div><h3 className="text-sm font-semibold text-white flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-purple-400" />Grounded Advisory Explanation</h3><p className="text-xs text-slate-400">Trade-off synthesis grounded in Pareto and Welch statistics</p></div>
                      <button onClick={runAdvisory} disabled={loadingAnalysis} className="px-2.5 py-1 bg-purple-600 text-white rounded text-xs flex items-center gap-1"><Sparkles className="w-3.5 h-3.5" />Generate</button>
                    </div>
                    {advisoryData ? (
                      <div className="space-y-2 text-xs">
                        <div className="p-2.5 bg-purple-950/30 border border-purple-800 rounded text-purple-200"><strong>Disclaimer: </strong>{advisoryData.disclaimer}</div>
                        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded whitespace-pre-wrap text-slate-300">{advisoryData.advisory_text}</div>
                        <div className="flex justify-between text-[11px] text-slate-500 font-mono"><span>Provider: {advisoryData.provider}</span><span>Fallback: {advisoryData.offline_fallback ? "Yes" : "No"}</span></div>
                      </div>
                    ) : <div className="text-center py-4 text-xs text-slate-500 border border-dashed border-slate-800 rounded">Click 'Generate' for advisory explanation.</div>}
                  </div>
                </div>
              )}

              {tab === "artifacts" && (
                <ArtifactRegistry artifacts={artifacts} runId={selectedRunArtifacts || runs[0]?.id} onRefresh={() => fetchArtifacts(selectedRunArtifacts || runs[0]?.id)} />
              )}
            </div>
          )}
        </main>
      </div>

      {showExpModal && (
        <M title="New Experiment" onClose={() => setShowExpModal(false)}>
          <form onSubmit={handleCreateExp} className="space-y-2 text-xs">
            <Inp label="Name" required {...bindE("name")} />
            <Inp label="Baseline Variant" {...bindE("baseline")} />
            <Inp label="Description" {...bindE("desc")} />
            <MF onCancel={() => setShowExpModal(false)} txt="Create" />
          </form>
        </M>
      )}

      {showImportModal && (
        <M title="Import Experiment Bundle" onClose={() => setShowImportModal(false)}>
          <form onSubmit={handleImportBundle} className="space-y-3 text-xs">
            <textarea rows={5} value={importJson} onChange={e => setImportJson(e.target.value)} placeholder='{"format": "bundle", ...}' className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-[11px] font-mono text-white" />
            <MF onCancel={() => setShowImportModal(false)} txt="Import" dis={importing || !importJson.trim()} />
          </form>
        </M>
      )}

      {showRunModal && selectedExp && (
        <M title="Log Run" onClose={() => setShowRunModal(false)}>
          <form onSubmit={handleCreateRun} className="space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <Inp label="Run Name" required {...bindR("name")} />
              <Inp label="Variant" required {...bindR("variant")} />
            </div>
            <Inp label="Seed" type="number" required value={newRun.seed} onChange={(e: any) => setR("seed", Number(e.target.value))} />
            <Inp label="Metrics (JSON)" required {...bindR("metrics")} />
            <Inp label="Hyperparams (JSON)" {...bindR("hp")} />
            <MF onCancel={() => setShowRunModal(false)} />
          </form>
        </M>
      )}

      {selectedRunDetail && (
        <M title={`Run: ${selectedRunDetail.name}`} onClose={() => setSelectedRunDetail(null)} maxW="max-w-xl">
          <div className="space-y-3 text-xs">
            <div className={`grid grid-cols-2 gap-2 ${box}`}>
              <div><span className="text-slate-500">Variant: </span><span className="text-blue-400 font-bold">{selectedRunDetail.variant_name}</span></div>
              <div><span className="text-slate-500">Seed: </span><span>{selectedRunDetail.seed}</span></div>
              <div><span className="text-slate-500">Status: </span><span className="text-emerald-400">{selectedRunDetail.status}</span></div>
              <div><span className="text-slate-500">Commit: </span><span>{selectedRunDetail.commit_hash || "N/A"}</span></div>
            </div>
            {selectedRunDetail.notes && <p className="text-slate-400 bg-slate-950/40 p-2 rounded border border-slate-800">{selectedRunDetail.notes}</p>}
            <div>
              <h4 className="font-semibold text-slate-300 mb-1 text-[11px]">Metrics</h4>
              <div className={`grid grid-cols-2 gap-1 ${box}`}>
                {Object.entries(selectedRunDetail.metrics).map(([k, v]) => (
                  <div key={k} className="flex justify-between p-1 bg-slate-900/60 rounded"><span className="text-slate-400">{k}:</span><span className="text-white font-bold">{typeof v === "number" ? v.toFixed(4) : v}</span></div>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => { setSelectedRunArtifacts(selectedRunDetail.id); setTab("artifacts"); setSelectedRunDetail(null); }} className={bSec}><FileCode className="w-3.5 h-3.5" />Artifacts</button>
              <button onClick={() => setSelectedRunDetail(null)} className={bPri}>Close</button>
            </div>
          </div>
        </M>
      )}

      {diffPair && <RunDiffModal baseRunId={diffPair.base} targetRunId={diffPair.target} onClose={() => setDiffPair(null)} />}

      {showAuditModal && (
        <M title="Security Audit Trail" onClose={() => setShowAuditModal(false)} maxW="max-w-2xl">
          <div className="max-h-[60vh] overflow-y-auto space-y-1 font-mono text-[11px]">
            {auditLogs.map(l => (
              <div key={l.id} className={`flex justify-between ${box}`}>
                <span className="text-blue-400">{l.user_email}</span>
                <span className="text-white font-bold">{l.action}</span>
                <span className="text-slate-400">{l.resource_type}:{l.resource_id}</span>
              </div>
            ))}
          </div>
        </M>
      )}
    </div>
  );
};

export default App;
