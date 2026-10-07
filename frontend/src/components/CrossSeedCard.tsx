import React from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { CrossSeedResult } from "../types";

export const CrossSeedCard: React.FC<{ data: CrossSeedResult }> = ({ data }) => {
  if (!data || !data.aggregations.length) {
    return <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-sm">No cross-seed metric aggregations.</div>;
  }

  return (
    <div className="space-y-6">
      {data.sample_size_warnings.length > 0 && (
        <div className="bg-amber-950/40 border border-amber-800 rounded-xl p-4 text-xs text-amber-300">
          <div className="flex items-center gap-2 font-semibold mb-1"><AlertTriangle className="w-4 h-4 text-amber-400" />Statistical Power Notice:</div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-200/90 font-mono text-[11px]">{data.sample_size_warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">Welch's Two-Sample t-Test & Non-Parametric Significance <span className="text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-mono">Baseline: {data.baseline_variant}</span></h3>
          <p className="text-xs text-slate-400 mt-1">Evaluated against random seed variance (two-tailed α = 0.05).</p>
        </div>

        {!data.hypothesis_tests.length ? (
          <div className="p-4 text-center text-xs text-slate-400 bg-slate-950 rounded-lg">Add at least two variants for comparative hypothesis testing.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
                <tr><th className="p-2">Variant</th><th className="p-2">Metric</th><th className="p-2 text-right">Base</th><th className="p-2 text-right">Treat</th><th className="p-2 text-right">Delta</th><th className="p-2 text-right">Welch p-value</th><th className="p-2 text-right">Cohen's d</th><th className="p-2 text-center">Result</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {data.hypothesis_tests.map((t, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40">
                    <td className="p-2 font-medium text-slate-200">{t.treatment_variant}</td>
                    <td className="p-2 font-mono text-slate-300">{t.metric}</td>
                    <td className="p-2 text-right font-mono text-slate-400">{t.baseline_mean.toFixed(4)}</td>
                    <td className="p-2 text-right font-mono text-slate-200">{t.treatment_mean.toFixed(4)}</td>
                    <td className="p-2 text-right font-mono"><span className={t.mean_delta > 0 ? "text-emerald-400" : "text-rose-400"}>{t.mean_delta > 0 ? "+" : ""}{t.mean_delta.toFixed(4)} ({t.percent_change.toFixed(1)}%)</span></td>
                    <td className="p-2 text-right font-mono font-bold"><span className={t.p_value_welch < 0.05 ? "text-amber-400" : "text-slate-400"}>{t.p_value_welch.toFixed(4)}</span></td>
                    <td className="p-2 text-right font-mono text-slate-300">{t.cohens_d.toFixed(2)}</td>
                    <td className="p-2 text-center"><span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-emerald-950 text-emerald-400 border border-emerald-800"><CheckCircle2 className="w-3 h-3" />Significant Gain</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-white">Confidence Intervals & Seed Variance Distribution (95% CI)</h3>
          <p className="text-xs text-slate-400 mt-1">Parametric Student's t-interval and non-parametric bootstrap resampling over evaluated seeds.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
              <tr><th className="p-2">Variant</th><th className="p-2">Metric</th><th className="p-2 text-center">N</th><th className="p-2 text-right">Mean ± Std</th><th className="p-2 text-right">Median [IQR]</th><th className="p-2 text-right">Student's t 95% CI</th><th className="p-2 text-right">Bootstrap 95% CI</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {data.aggregations.map((agg, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40">
                  <td className="p-2 font-sans font-medium text-slate-200">{agg.variant_name}</td>
                  <td className="p-2 text-slate-300 font-semibold">{agg.metric}</td>
                  <td className="p-2 text-center text-slate-400"><span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">N={agg.sample_size_n}</span></td>
                  <td className="p-2 text-right text-slate-200 font-bold">{agg.mean.toFixed(4)} <span className="text-slate-400 font-normal">± {agg.std_dev.toFixed(4)}</span></td>
                  <td className="p-2 text-right text-slate-300">{agg.median.toFixed(4)} <span className="text-slate-400">[{agg.iqr.toFixed(4)}]</span></td>
                  <td className="p-2 text-right text-blue-400">[{agg.ci_t_distribution.lower.toFixed(4)}, {agg.ci_t_distribution.upper.toFixed(4)}]</td>
                  <td className="p-2 text-right text-emerald-400">[{agg.ci_bootstrap.lower.toFixed(4)}, {agg.ci_bootstrap.upper.toFixed(4)}]</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
