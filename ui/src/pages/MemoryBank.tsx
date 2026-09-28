import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import { Brain, Search, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

interface Memory {
  incident_id: string;
  symptoms: string;
  root_cause: string;
  playbook: string[];
  success_rate: number;
  outcome: string;
  human_approved: boolean;
}

interface MemoryBankResponse {
  bank_id: string;
  total_memories: number;
  memories: Memory[];
}

export const MemoryBank = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery<MemoryBankResponse>({
    queryKey: ["memory-bank"],
    queryFn: async () => (await apiClient.get("/memory/bank")).data,
    refetchInterval: 5000,
  });

  const memories = data?.memories || [];
  
  const filtered = memories.filter((m) => {
    const q = search.toLowerCase();
    return (
      m.symptoms.toLowerCase().includes(q) ||
      m.root_cause.toLowerCase().includes(q) ||
      m.incident_id.toLowerCase().includes(q)
    );
  });

  const getOutcomeVariant = (outcome: string) => {
    switch (outcome) {
      case "success": return "success";
      case "human_validated": return "default";
      case "human_modified": return "warning";
      case "human_rejected": return "destructive";
      default: return "secondary";
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Brain className="text-indigo-500" />
            Hindsight Memory Bank
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Persistent semantic memory of past incidents, root causes, and proven playbooks.
          </p>
        </div>
        {data && (
          <div className="flex items-center gap-3 bg-white border border-slate-200 px-3 py-1.5 rounded-full shadow-sm text-xs font-medium text-slate-700">
            <div className="flex items-center gap-1.5 border-r border-slate-200 pr-3">
              <ShieldCheck size={14} className="text-emerald-500" />
              Connected to Hindsight Cloud
            </div>
            <div className="pl-1">
              <span className="font-mono text-indigo-600 mr-1.5">{data.bank_id}</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded-full">{data.total_memories} entries</span>
            </div>
          </div>
        )}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search semantic memory by symptoms or root cause..."
          className="pl-9 bg-white"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className="py-20 text-center text-slate-500">Loading semantic memory...</div>
      ) : filtered.length === 0 ? (
        <Card className="border-dashed bg-slate-50/50">
          <CardContent className="flex flex-col items-center justify-center py-20 text-center">
            <Brain size={48} className="text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-700">No memories retained yet.</h3>
            <p className="text-sm text-slate-500 max-w-sm mt-2 mb-6">
              The memory bank is empty. Run your first diagnostic or simulate an incident to seed the semantic memory.
            </p>
            <button
              onClick={() => navigate("/")}
              className="px-4 py-2 bg-slate-900 text-white rounded-md text-sm font-medium hover:bg-slate-800 transition-colors"
            >
              Return to Dashboard
            </button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((m, idx) => (
            <Card
              key={m.incident_id}
              className="animate-fade-in hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5"
              style={{animationDelay: `${idx * 50}ms`}}
            >
              <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
                <CardTitle className="text-[11px] font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                  {m.incident_id}
                </CardTitle>
                <Badge variant={getOutcomeVariant(m.outcome)} className="text-[10px] capitalize">
                  {m.outcome.replace('_', ' ')}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Symptoms</h4>
                  <p className="font-medium text-slate-800 leading-snug">{m.symptoms}</p>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Root Cause</h4>
                  <p className="text-sm text-slate-600">{m.root_cause}</p>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <h4 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Automated Playbook</h4>
                  <ol className="list-decimal list-inside text-xs text-slate-700 space-y-1">
                    {m.playbook.map((step, idx) => (
                      <li key={idx} className="truncate">{step}</li>
                    ))}
                  </ol>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                  <span className="text-[10px] font-medium text-slate-400 uppercase">Confidence</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full animate-bar-grow"
                        style={{ width: `${m.success_rate * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-slate-600">{(m.success_rate * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
