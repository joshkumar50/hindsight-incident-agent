import React from "react";
import { BrainCircuit, Search } from "lucide-react";

export interface MemoryHitBadgeProps {
  mode: "recall" | "fresh";
  durationSeconds: number;
  confidence: number;
}

export const MemoryHitBadge: React.FC<MemoryHitBadgeProps> = ({ mode, durationSeconds, confidence }) => {
  const isRecall = mode === "recall";

  const containerClasses = isRecall
    ? "bg-violet-50 border-violet-200"
    : "bg-amber-50 border-amber-200";

  const iconClasses = isRecall ? "text-violet-600" : "text-amber-600";
  const titleClasses = isRecall ? "text-violet-700" : "text-amber-700";
  const subtitleClasses = isRecall ? "text-violet-600" : "text-amber-600";
  const Icon = isRecall ? BrainCircuit : Search;
  const titleText = isRecall ? "HINDSIGHT RECALL HIT" : "FRESH REASONING";
  const subtitleText = isRecall 
    ? `${durationSeconds}s · 0 LLM tokens · playbook from memory`
    : `${durationSeconds}s · ReAct loop · playbook retained to memory`;

  return (
    <div className={`w-full flex items-center justify-between border rounded-lg px-4 py-3 ${containerClasses}`}>
      <div className="flex items-center gap-3">
        <Icon className={iconClasses} size={20} />
        <div className="flex flex-col">
          <span className={`text-xs font-semibold tracking-wider ${titleClasses}`}>
            {titleText}
          </span>
          <span className={`text-xs ${subtitleClasses}`}>
            {subtitleText}
          </span>
        </div>
      </div>
      <div className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-bold ${isRecall ? "bg-violet-200 text-violet-800" : "bg-amber-200 text-amber-800"}`}>
        {(confidence * 100).toFixed(0)}% CONF
      </div>
    </div>
  );
};
