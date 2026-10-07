import React, { useEffect, useState } from "react";
import { AlertCircle, BarChart2, CheckCircle2, ChevronRight, Cpu, Download, FileCode, FileSpreadsheet, GitCompare, Layers, Plus, RefreshCw, Search, Sparkles, Trash2, X } from "lucide-react";
import { api } from "./api/client";
import { ArtifactRegistry } from "./components/ArtifactRegistry";
import { CrossSeedCard } from "./components/CrossSeedCard";
import { Navbar } from "./components/Navbar";
import { ParetoChart } from "./components/ParetoChart";
import { RunDiffModal } from "./components/RunDiffModal";
import { useAuth } from "./context/AuthContext";
import { AdvisoryExplanationResult, Artifact, AuditLogItem, CrossSeedResult, Experiment, ParetoFrontierResult, Run, SensitivityResult } from "./types";

const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode; maxW?: string }> = ({ title, onClose, children, maxW = "max-w-md" }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75">
    <div className={`bg-slate-900 border border-slate-800 rounded-xl ${maxW} w-full p-4 space-y-3 shadow-2xl`}>
      <div className="flex justify-between items-center"><h3 className="text-sm font-bold text-white">{title}</h3><button onClick={onClose}><X className="w-4 h-4 text-slate-400" /></button></div>
      {children}
    </div>
  </div>
);

const Inp: React.FC<{ label: string; [k: string]: any }> = ({ label, ...p }) => (
  <div><label className="block text-slate-300 text-xs mb-1">{label}</label><input className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white" {...p} /></div>
);

export const App: React.FC = () => {
  const { isAdmin, isAnalyst } = useAuth();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null);
  const [loadingExp, setLoadingExp] = useState(false);
  const [expSearch, setExpSearch] = useState("");
  const [showExpModal, setShowExpModal] = useState(false);
  const [newExp, setNewExp] = useState({ name: "", desc: "", domain: "ai-ml", baseline: "baseline" });
  const [tab, setTab] = useState<"runs" | "pareto" | "cross_seed" | "sensitivity" | "artifacts">("runs");

  const [runs, setRuns] = useState<Run[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [selDiff, setSelDiff] = useState<string[]>([]);
  const [diffPair, setDiffPair] = useState<{ base: string; target: string } | null>(null);
  const [showRunModal, setShowRunModal] = useState(false);
  const [newRun, setNewRun] = useState({ name: "", variant: "variant_a", seed: 42, metrics: '{"accuracy": 0.88, "latency_ms": 12.4}', hp: '{"lr": 0.001}' });

  const [paretoData, setParetoData] = useState<ParetoFrontierResult | null>(null);
  const [crossSeedData, setCrossSeedData] = useState<CrossSeedResult | null>(null);
  const [sensitivityData, setSensitivityData] = useState<SensitivityResult | null>(null);
  const [advisoryData, setAdvisoryData] = useState<AdvisoryExplanationResult | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedRunArtifacts, setSelectedRunArtifacts] = useState<string | undefined>();
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchExperiments = async () => {
    setLoadingExp(true);
    try {
      const res = await api.experiments.list(1, 50, expSearch);
      setExperiments(res.items);
      if (res.items.length && !selectedExp) setSelectedExp(res.items[0]);
      else if (selectedExp) setSelectedExp(res.items.find(e => e.id === selectedExp.id) || res.items[0] || null);
    } catch (e: any) { setMsg({ type: "error", text: e.message || "Failed to load experiments" }); }
    finally { setLoadingExp(false); }
  };

  useEffect(() => { fetchExperiments(); }, [expSearch]);

  const fetchRuns = async (id: string) => {
    setLoadingRuns(true);
    try { setRuns((await api.runs.list(id, 1, 100)).items); setSelDiff([]); }
    catch (e: any) { setMsg({ type: "error", text: e.message || "Failed to fetch runs" }); }
    finally { setLoadingRuns(false); }
  };

  const fetchArtifacts = async (id?: string) => {
    const target = id || runs[0]?.id;
    if (!target) { setArtifacts([]); return; }
    try { setArtifacts(await api.artifacts.list(target)); } catch { setArtifacts([]); }
  };

  useEffect(() => {
    if (selectedExp) {
      fetchRuns(selectedExp.id);
      setParetoData(null); setCrossSeedData(null); setSensitivityData(null); setAdvisoryData(null);
    }
  }, [selectedExp?.id]);

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
    } catch (err: any) { setMsg({ type: "error", text: err.message || "Failed to create run" }); }
  };

  const handleDeleteRun = async (id: string) => {
    if (!confirm("Delete run?")) return;
    try { await api.runs.delete(id); if (selectedExp) fetchRuns(selectedExp.id); } catch {}
  };

  const toggleDiff = (id: string) => setSelDiff(p => p.includes(id) ? p.filter(x => x !== id) : p.length >= 2 ? [p[1], id] : [...p, id]);

  const runPareto = async () => {
    if (!selectedExp) return;
    setLoadingAnalysis(true); setAnalysisError(null);
    try { setParetoData(await api.analysis.pareto(selectedExp.id, [{ metric: "accuracy", direction: "maximize" }, { metric: "latency_ms", direction: "minimize" }])); }
    catch (e: any) { setAnalysisError(e.message || "Pareto failed"); }
    finally { setLoadingAnalysis(false); }
  };

  const runCrossSeed = async () => {
    if (!selectedExp) return;
    setLoadingAnalysis(true); setAnalysisError(null);
    try { setCrossSeedData(await api.analysis.crossSeed(selectedExp.id, ["accuracy", "latency_ms"], selectedExp.baseline_variant || undefined)); }
    catch (e: any) { setAnalysisError(e.message || "Cross-seed failed"); }
    finally { setLoadingAnalysis(false); }
  };

  const runSensitivity = async () => {
    if (!selectedExp) return;
    setLoadingAnalysis(true); setAnalysisError(null);
    try { setSensitivityData(await api.analysis.sensitivity(selectedExp.id, "accuracy")); } catch {}
    finally { setLoadingAnalysis(false); }
  };

  const runAdvisory = async () => {
    if (!selectedExp) return;
    setLoadingAnalysis(true);
    try { setAdvisoryData(await api.analysis.advisory(selectedExp.id, "comprehensive")); }
    catch (e: any) { setMsg({ type: "error", text: e.message || "Advisory failed" }); }
    finally { setLoadingAnalysis(false); }
  };

  const exportBundle = async () => {
    if (!selectedExp) return;
    try {
      const b = await api.bundles.export(selectedExp.id);
      const url = URL.createObjectURL(new Blob([JSON.stringify(b, null, 2)], { type: "application/json" }));
      const a = document.createElement("a"); a.href = url; a.download = `exp_${selectedExp.id}.json`; a.click();
    } catch {}
  };

  const loadAudit = async () => {
    setShowAuditModal(true);
    try { setAuditLogs((await api.audit.list(1, 50)).items); } catch {}
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar onOpenAuditLogs={loadAudit} onNavigateHome={() => setSelectedExp(null)} />
      {msg && (
        <div className={`px-4 py-2 text-xs flex justify-between border-b ${msg.type === "success" ? "bg-emerald-950/80 border-emerald-800 text-emerald-300" : "bg-rose-950/80 border-rose-800 text-rose-300"}`}>
          <div className="flex items-center gap-2">{msg.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}<span>{msg.text}</span></div>
          <button onClick={() => setMsg(null)}><X className="w-4 h-4" /></button>
        </div>
      )}
      <div className="flex-1 flex max-w-7xl w-full mx-auto p-4 sm:p-6 gap-6">
        <aside className="w-80 shrink-0 flex flex-col bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-1.5"><Layers className="w-4 h-4 text-blue-400" />Experiments</h2>
            {isAnalyst && <button onClick={() => setShowExpModal(true)} className="p-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"><Plus className="w-4 h-4" /></button>}
          </div>
          <div className="relative mb-3">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input type="text" placeholder="Search..." value={expSearch} onChange={e => setExpSearch(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white" />
          </div>
          <div className="flex-1 overflow-y-auto space-y-2">
            {loadingExp && <div className="text-center py-6 text-xs text-slate-500">Loading...</div>}
            {!loadingExp && !experiments.length && <div className="text-center py-8 text-xs text-slate-500">No experiments.</div>}
            {experiments.map(exp => (
              <div key={exp.id} onClick={() => setSelectedExp(exp)} className={`p-3 rounded-lg cursor-pointer border ${selectedExp?.id === exp.id ? "bg-blue-950/40 border-blue-600 text-white" : "bg-slate-950/40 border-slate-800 text-slate-300"}`}>
                <div className="flex justify-between"><span className="font-semibold text-xs truncate max-w-[180px]">{exp.name}</span><ChevronRight className="w-3.5 h-3.5 text-slate-500" /></div>
                <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono"><span>{exp.domain}</span><span>{exp.run_count || 0} runs</span></div>
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
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl flex justify-between items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-white">{selectedExp.name}</h2>
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono">{selectedExp.domain}</span>
                    {selectedExp.baseline_variant && <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">baseline: {selectedExp.baseline_variant}</span>}
                  </div>
                  {selectedExp.description && <p className="text-xs text-slate-400 mt-0.5">{selectedExp.description}</p>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => window.open(`/api/v1/export/runs.csv?experiment_id=${selectedExp.id}`, "_blank")} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs flex items-center gap-1"><FileSpreadsheet className="w-3.5 h-3.5" />CSV</button>
                  <button onClick={exportBundle} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs flex items-center gap-1"><Download className="w-3.5 h-3.5" />Export</button>
                  {isAdmin && <button onClick={() => handleDeleteExp(selectedExp.id)} className="p-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded"><Trash2 className="w-3.5 h-3.5" /></button>}
                </div>
              </div>

              <div className="flex border-b border-slate-800 gap-2">
                {[
                  { k: "runs", l: `Runs (${runs.length})`, i: Layers },
                  { k: "pareto", l: "Pareto Frontier", i: BarChart2 },
                  { k: "cross_seed", l: "Cross-Seed Stats", i: GitCompare },
                  { k: "sensitivity", l: "Sensitivity & Advisory", i: Sparkles },
                  { k: "artifacts", l: "Artifacts", i: FileCode },
                ].map(t => (
                  <button key={t.k} onClick={() => setTab(t.k as any)} className={`px-3 py-2 text-xs font-semibold flex items-center gap-1.5 border-b-2 ${tab === t.k ? "border-blue-500 text-white bg-slate-900/60" : "border-transparent text-slate-400"}`}><t.i className="w-3.5 h-3.5" />{t.l}</button>
                ))}
              </div>

              {tab === "runs" && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <div className="flex items-center gap-2 text-slate-400">
                      <span>Diff: {selDiff.length}/2</span>
                      {selDiff.length === 2 && <button onClick={() => setDiffPair({ base: selDiff[0], target: selDiff[1] })} className="px-2 py-0.5 bg-emerald-600 text-white rounded flex items-center gap-1"><GitCompare className="w-3 h-3" />Compare</button>}
                    </div>
                    {isAnalyst && <button onClick={() => setShowRunModal(true)} className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded flex items-center gap-1"><Plus className="w-3.5 h-3.5" />Log Run</button>}
                  </div>
                  {loadingRuns ? <div className="text-center py-4 text-xs text-slate-400">Loading...</div> : !runs.length ? <div className="text-center py-4 text-xs text-slate-500">No runs logged.</div> : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                          <tr><th className="p-2">Diff</th><th className="p-2">Name</th><th className="p-2">Variant</th><th className="p-2">Seed</th><th className="p-2">Metrics</th><th className="p-2">Hyperparams</th><th className="p-2 text-right">Actions</th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-sans">
                          {runs.map(r => (
                            <tr key={r.id} className="hover:bg-slate-800/40">
                              <td className="p-2"><input type="checkbox" checked={selDiff.includes(r.id)} onChange={() => toggleDiff(r.id)} /></td>
                              <td className="p-2 font-semibold text-white">{r.name}</td>
                              <td className="p-2 font-mono text-blue-400">{r.variant_name}</td>
                              <td className="p-2 font-mono text-slate-400">{r.seed}</td>
                              <td className="p-2 font-mono text-[11px] text-slate-300">{Object.entries(r.metrics).map(([k, v]) => `${k}:${v.toFixed(3)}`).join(" ")}</td>
                              <td className="p-2 font-mono text-[11px] text-slate-400">{Object.entries(r.hyperparameters).map(([k, v]) => `${k}:${v}`).join(", ")}</td>
                              <td className="p-2 text-right">
                                <button onClick={() => { setSelectedRunArtifacts(r.id); setTab("artifacts"); }} className="p-1 text-slate-400 hover:text-white mr-1"><FileCode className="w-3.5 h-3.5" /></button>
                                {isAnalyst && <button onClick={() => handleDeleteRun(r.id)} className="p-1 text-slate-500 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {tab === "pareto" && (
                <div className="space-y-3">
                  <div className="flex justify-end"><button onClick={runPareto} disabled={loadingAnalysis} className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs flex items-center gap-1"><RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? "animate-spin" : ""}`} />Recompute</button></div>
                  {analysisError && <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs">{analysisError}</div>}
                  {paretoData ? <ParetoChart data={paretoData} onSelectRun={id => alert(`Selected Run: ${id}`)} /> : <div className="p-6 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-xs">No Pareto data.</div>}
                </div>
              )}

              {tab === "cross_seed" && (
                <div className="space-y-3">
                  <div className="flex justify-end"><button onClick={runCrossSeed} disabled={loadingAnalysis} className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs flex items-center gap-1"><RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? "animate-spin" : ""}`} />Recalculate</button></div>
                  {analysisError && <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs">{analysisError}</div>}
                  {crossSeedData ? <CrossSeedCard data={crossSeedData} /> : <div className="p-6 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-xs">No cross-seed statistics.</div>}
                </div>
              )}

              {tab === "sensitivity" && (
                <div className="space-y-4">
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
                    <div className="flex justify-between items-center">
                      <div><h3 className="text-sm font-semibold text-white">Hyperparameter Sensitivity</h3><p className="text-xs text-slate-400">Spearman correlation & feature importance</p></div>
                      <button onClick={runSensitivity} disabled={loadingAnalysis} className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded text-xs flex items-center gap-1"><RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? "animate-spin" : ""}`} />Refresh</button>
                    </div>
                    {sensitivityData?.parameters.length ? (
                      <div className="space-y-1.5">
                        {sensitivityData.parameters.map(p => (
                          <div key={p.parameter} className="p-2.5 bg-slate-950/50 border border-slate-800 rounded flex justify-between text-xs">
                            <div><span className="font-mono font-bold text-white">{p.parameter}</span><span className="ml-2 text-slate-400">({p.parameter_type})</span><p className="text-[11px] text-slate-400 mt-0.5">{p.summary}</p></div>
                            <div className="text-right font-mono text-blue-400 font-bold">{(p.importance_score * 100).toFixed(1)}%</div>
                          </div>
                        ))}
                      </div>
                    ) : <div className="text-center py-4 text-xs text-slate-500">No parameter variance.</div>}
                  </div>

                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
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
                    ) : <div className="text-center py-4 text-xs text-slate-500 border border-dashed border-slate-800 rounded">Click "Generate" to synthesize an advisory explanation.</div>}
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
        <Modal title="New Experiment" onClose={() => setShowExpModal(false)}>
          <form onSubmit={handleCreateExp} className="space-y-2 text-xs">
            <Inp label="Name" required value={newExp.name} onChange={(e: any) => setNewExp({ ...newExp, name: e.target.value })} />
            <Inp label="Baseline" value={newExp.baseline} onChange={(e: any) => setNewExp({ ...newExp, baseline: e.target.value })} />
            <Inp label="Description" value={newExp.desc} onChange={(e: any) => setNewExp({ ...newExp, desc: e.target.value })} />
            <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setShowExpModal(false)} className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded">Cancel</button><button type="submit" className="px-3 py-1 bg-blue-600 text-white rounded">Create</button></div>
          </form>
        </Modal>
      )}

      {showRunModal && selectedExp && (
        <Modal title="Log Run" onClose={() => setShowRunModal(false)}>
          <form onSubmit={handleCreateRun} className="space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <Inp label="Run Name" required value={newRun.name} onChange={(e: any) => setNewRun({ ...newRun, name: e.target.value })} />
              <Inp label="Variant" required value={newRun.variant} onChange={(e: any) => setNewRun({ ...newRun, variant: e.target.value })} />
            </div>
            <Inp label="Seed" type="number" required value={newRun.seed} onChange={(e: any) => setNewRun({ ...newRun, seed: Number(e.target.value) })} />
            <Inp label="Metrics (JSON)" required value={newRun.metrics} onChange={(e: any) => setNewRun({ ...newRun, metrics: e.target.value })} />
            <Inp label="Hyperparams (JSON)" value={newRun.hp} onChange={(e: any) => setNewRun({ ...newRun, hp: e.target.value })} />
            <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setShowRunModal(false)} className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded">Cancel</button><button type="submit" className="px-3 py-1 bg-blue-600 text-white rounded">Save</button></div>
          </form>
        </Modal>
      )}

      {diffPair && <RunDiffModal baseRunId={diffPair.base} targetRunId={diffPair.target} onClose={() => setDiffPair(null)} />}

      {showAuditModal && (
        <Modal title="Security Audit Trail" onClose={() => setShowAuditModal(false)} maxW="max-w-2xl">
          <div className="max-h-[60vh] overflow-y-auto space-y-1.5 font-mono text-xs">
            {!auditLogs.length ? <div className="text-center py-4 text-slate-500">No audit events recorded.</div> : auditLogs.map(l => (
              <div key={l.id} className="p-2 bg-slate-950 border border-slate-800 rounded flex justify-between items-center text-[11px]">
                <span className="text-slate-400">{new Date(l.timestamp).toLocaleTimeString()}</span>
                <span className="text-blue-400 font-semibold">{l.user_email}</span>
                <span className="text-white font-bold">{l.action}</span>
                <span className="text-slate-300">{l.resource_type}:{l.resource_id}</span>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  );
};

export default App;
