import React from "react";
import { AlertTriangle, ArrowRight, ChevronDown, ChevronUp, Info, Sparkles, TrendingUp, Zap } from "lucide-react";
import { TuningRecommendationsResponse, TuningRecommendation } from "../types";

interface TuningRecommendationsProps {
  data: TuningRecommendationsResponse;
  onRefresh: () => void;
  availableMetrics: string[];
}

const PRIORITY_COLORS: Record<TuningRecommendation["priority"], string> = {
  high: "bg-rose-950/60 border-rose-700 text-rose-300",
  medium: "bg-amber-950/60 border-amber-700 text-amber-300",
  low: "bg-emerald-950/60 border-emerald-700 text-emerald-300",
};

const PRIORITY_ICONS: Record<TuningRecommendation["priority"], React.ReactNode> = {
  high: <Zap className="w-3.5 h-3.5 text-rose-400" />,
  medium: <TrendingUp className="w-3.5 h-3.5 text-amber-400" />,
  low: <Info className="w-3.5 h-3.5 text-emerald-400" />,
};

const SOURCE_LABELS: Record<TuningRecommendation["source"], string> = {
  sensitivity: "Sensitivity Analysis",
  pareto_knee: "Pareto Knee Point",
  combined: "Combined Evidence",
};

const SOURCE_ICONS: Record<TuningRecommendation["source"], React.ReactNode> = {
  sensitivity: <Sparkles className="w-3 h-3 text-purple-400" />,
  pareto_knee: <ArrowRight className="w-3 h-3 text-blue-400" />,
  combined: <Zap className="w-3 h-3 text-yellow-400" />,
};

const formatRange = (range: any[]): string => {
  if (!range || range.length === 0) return "—";
  if (range.length === 1) return String(range[0]);
  if (typeof range[0] === "number" && typeof range[1] === "number") {
    return `[${range[0].toFixed(4)}, ${range[1].toFixed(4)}]`;
  }
  return range.map(String).join(", ");
};

const formatValue = (val: any): string => {
  if (typeof val === "number") return val.toFixed(4);
  return String(val);
};

const TuningRecommendations: React.FC<TuningRecommendationsProps> = ({
  data,
  onRefresh,
  availableMetrics,
}) => {
  const [expandedIds, setExpandedIds] = React.useState<Set<string>>(new Set());

  const toggleExpand = (param: string) => {
    const newSet = new Set(expandedIds);
    if (newSet.has(param)) newSet.delete(param);
    else newSet.add(param);
    setExpandedIds(newSet);
  };

  const { recommendations, sensitivity_summary, pareto_knee_config, target_metric, experiment_id } = data;

  if (!recommendations.length) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
        <Info className="w-8 h-8 mx-auto text-slate-600 mb-2" />
        <p className="font-medium text-slate-400">No tuning recommendations generated</p>
        <p className="text-[11px] mt-1">Try adding more runs with varied hyperparameters to enable sensitivity analysis.</p>
      </div>
    );
  }

  const highPriorityCount = recommendations.filter(r => r.priority === "high").length;
  const mediumPriorityCount = recommendations.filter(r => r.priority === "medium").length;
  const lowPriorityCount = recommendations.filter(r => r.priority === "low").length;

  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-purple-400" />
              Hyperparameter Tuning Recommendations
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Target metric: <span className="font-mono text-white ml-1">{target_metric}</span>
              {" | Experiment: "}{experiment_id.slice(0, 8)}...
            </p>
          </div>
          <button onClick={onRefresh} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs flex items-center gap-1 border border-slate-700">
            <Zap className="w-3 h-3" />Refresh
          </button>
        </div>

        <div className="flex flex-wrap gap-2 text-[11px]">
          <span className="px-2 py-0.5 bg-rose-950/60 border border-rose-700 text-rose-300 rounded">
            High: {highPriorityCount}
          </span>
          <span className="px-2 py-0.5 bg-amber-950/60 border border-amber-700 text-amber-300 rounded">
            Medium: {mediumPriorityCount}
          </span>
          <span className="px-2 py-0.5 bg-emerald-950/60 border border-emerald-700 text-emerald-300 rounded">
            Low: {lowPriorityCount}
          </span>
          <span className="px-2 py-0.5 bg-purple-950/60 border border-purple-700 text-purple-300 rounded">
            Total: {recommendations.length}
          </span>
        </div>

        {pareto_knee_config && Object.keys(pareto_knee_config).length > 0 && (
          <div className="p-3 bg-blue-950/40 border border-blue-800/40 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-blue-300 mb-1">
              <ArrowRight className="w-3.5 h-3.5" />
              <span className="font-medium">Pareto Knee Point Configuration</span>
            </div>
            <div className="flex flex-wrap gap-2 text-[11px] font-mono text-blue-200">
              {Object.entries(pareto_knee_config).map(([k, v]) => (
                <span key={k} className="bg-blue-950/60 border border-blue-800 px-1.5 py-0.5 rounded">
                  {k}: {formatValue(v)}
                </span>
              ))}
            </div>
          </div>
        )}

        {sensitivity_summary && Object.keys(sensitivity_summary).length > 0 && (
          <div className="p-3 bg-purple-950/40 border border-purple-800/40 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-purple-300 mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span className="font-medium">Sensitivity Summary</span>
            </div>
            <div className="flex flex-wrap gap-2 text-[11px] font-mono text-purple-200">
              {Object.entries(sensitivity_summary).map(([k, v]) => (
                <span key={k} className="bg-purple-950/60 border border-purple-800 px-1.5 py-0.5 rounded">
                  {k}: {typeof v === "number" ? v.toFixed(3) : v}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {recommendations.map((rec, idx) => {
            const isExpanded = expandedIds.has(rec.parameter);
            const priorityClass = PRIORITY_COLORS[rec.priority];
            const priorityIcon = PRIORITY_ICONS[rec.priority];
            const sourceLabel = SOURCE_LABELS[rec.source];
            const sourceIcon = SOURCE_ICONS[rec.source];

            return (
              <div
                key={`${rec.parameter}-${idx}`}
                className={`border rounded-xl overflow-hidden transition-all ${priorityClass}`}
              >
                <button
                  onClick={() => toggleExpand(rec.parameter)}
                  className="w-full p-3 flex items-center justify-between gap-3 text-left"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {priorityIcon}
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-white truncate">{rec.parameter}</span>
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-slate-900 border border-slate-700 text-slate-300">
                          {rec.parameter_type}
                        </span>
                        <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded flex items-center gap-0.5 ${priorityClass.replace("border-", "border-").replace("text-", "text-")}`}>
                          {sourceIcon} {sourceLabel}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5 truncate">{rec.rationale}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${priorityClass.replace("bg-", "bg-").replace("border-", "border-").replace("text-", "text-")}`}>
                      {rec.priority.toUpperCase()}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">Conf: {(rec.confidence * 100).toFixed(0)}%</span>
                    <div className="flex items-center gap-1">
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-slate-800/50 animate-slide-down bg-slate-950/30">
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      <div className="space-y-1">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wide">Current Range</span>
                        <div className="p-2 bg-slate-900 border border-slate-800 rounded font-mono text-[11px] text-white">
                          {formatRange(rec.current_range)}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wide">Recommended Range</span>
                        <div className="p-2 bg-emerald-950/40 border border-emerald-800/40 rounded font-mono text-[11px] text-emerald-300">
                          {formatRange(rec.recommended_range)}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 p-2 bg-slate-900/50 border border-slate-800/50 rounded text-[11px] text-slate-300">
                      <span className="text-slate-500">Confidence: </span>
                      <span className="font-mono font-bold text-white">{(rec.confidence * 100).toFixed(1)}%</span>
                      <span className="ml-4 text-slate-500">Priority: </span>
                      <span className={`font-bold ${priorityClass.replace("bg-", "text-").replace("border-", "").replace("text-", "")}`}>
                        {rec.priority.toUpperCase()}
                      </span>
                      <span className="ml-4 text-slate-500">Source: </span>
                      <span className="font-mono text-blue-400">{sourceLabel}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
};

export { TuningRecommendations };
