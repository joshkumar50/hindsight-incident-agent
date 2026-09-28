import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import {
  Activity, AlertTriangle, Brain, ChevronRight, Clock,
  DollarSign, FlaskConical, Search, Server, ShieldCheck,
  Zap, CheckCircle2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { MemoryHitBadge } from "../components/MemoryHitBadge";
import { useStore } from "../store/useStore";

/* ─── API shapes ─────────────────────────────────────────── */
interface DashboardData {
  cluster_health: string; app_health: string; platform_health: string;
  mttr_seconds: number; active_incidents: number;
  recovered_incidents: number; system_availability: number;
}
interface Incident {
  id: string; description: string; status: string; severity: string;
  root_cause: string; impacted_services: string[]; timestamp: number;
}
interface IncidentsResponse { value: Incident[]; Count: number; }
interface MemoryEntry {
  incident_id: string; symptoms: string; root_cause: string;
  success_rate: number; outcome: string;
}
interface MemoryResponse { memories: MemoryEntry[]; total: number; }

/* ─── helpers ────────────────────────────────────────────── */
function timeAgo(ts: number): string {
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

function statusVariant(status: string): "investigating" | "resolved" | "secondary" {
  if (status === "investigating") return "investigating";
  if (status === "resolved") return "resolved";
  return "secondary";
}

function severityDot(severity: string): string {
  if (severity === "critical") return "bg-red-500";
  if (severity === "high") return "bg-orange-500";
  if (severity === "medium") return "bg-amber-400";
  return "bg-slate-300";
}

/* ─── Incident slide-over ────────────────────────────────── */
function IncidentSheet({ incident, onClose }: { incident: Incident; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="flex-1 bg-black/20" />
      <div
        className="w-full max-w-md bg-white shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <span className="font-mono text-xs font-semibold text-slate-900">{incident.id}</span>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg leading-none">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-sm">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Status</p>
            <Badge variant={statusVariant(incident.status)}>{incident.status}</Badge>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Symptoms</p>
            <p className="text-slate-700">{incident.description}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Root Cause</p>
            <p className="text-slate-900 font-medium">{incident.root_cause}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Impacted Services</p>
            <div className="flex flex-wrap gap-1.5">
              {incident.impacted_services.length > 0
                ? incident.impacted_services.map(s => (
                    <Badge key={s} variant="secondary">{s}</Badge>
                  ))
                : <span className="text-slate-400 text-xs">—</span>}
            </div>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Severity</p>
            <Badge variant={incident.severity === "high" || incident.severity === "critical" ? "destructive" : "secondary"}>
              {incident.severity}
            </Badge>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Opened</p>
            <p className="text-slate-700 font-mono">{timeAgo(incident.timestamp)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ──────────────────────────────────────────── */
export const ExecutiveDashboard = () => {
  const navigate = useNavigate();
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const { lastDiagnostic } = useStore();

  const { data: dash } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: async () => (await apiClient.get("/dashboard")).data,
  });
  const { data: incData } = useQuery<IncidentsResponse>({
    queryKey: ["incidents"],
    queryFn: async () => (await apiClient.get("/incidents")).data,
    refetchInterval: 3000,
  });
  const { data: memData } = useQuery<MemoryResponse>({
    queryKey: ["memory"],
    queryFn: async () => (await apiClient.get("/memory/bank")).data,
  });

  const incidents = incData?.value ?? [];
  const memories = memData?.memories?.slice(0, 3) ?? [];

  const avail = dash?.system_availability ?? 99.99;
  const mttr = dash?.mttr_seconds ?? 0;
  const active = dash?.active_incidents ?? incidents.filter(i => i.status === "investigating").length;
  const recovered = dash?.recovered_incidents ?? incidents.filter(i => i.status === "resolved").length;

  const kpis = [
    {
      label: "AVAILABILITY",
      value: `${avail}%`,
      delta: "+0.01%",
      positive: true,
      icon: <ShieldCheck size={12} className="text-slate-400" />,
    },
    {
      label: "MTTR",
      value: mttr > 0 ? `${mttr}s` : "—",
      delta: "−2.1s vs last wk",
      positive: true,
      icon: <Clock size={12} className="text-slate-400" />,
    },
    {
      label: "ACTIVE",
      value: String(active),
      delta: active === 0 ? "All clear" : "Needs attn",
      positive: active === 0,
      icon: <AlertTriangle size={12} className="text-slate-400" />,
    },
    {
      label: "RECOVERED",
      value: String(recovered),
      delta: "Autonomous",
      positive: true,
      icon: <Activity size={12} className="text-slate-400" />,
    },
    {
      label: "MEMORIES",
      value: String(memData?.total ?? memories.length),
      delta: "Hindsight bank",
      positive: true,
      icon: <Brain size={12} className="text-slate-400" />,
    },
  ];

  return (
    <div className="space-y-4 max-w-6xl mx-auto animate-fade-in">

      {/* ── 1. KPI STRIP ──────────────────────────────────────── */}
      <Card>
        <div className="grid grid-cols-3 md:grid-cols-5 divide-x divide-slate-100">
          {kpis.map(k => (
            <div key={k.label} className="px-4 py-3 flex flex-col gap-1 transition-all duration-300 hover:bg-slate-50/80 hover:shadow-sm">
              <div className="flex items-center gap-1">
                {k.icon}
                <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{k.label}</span>
              </div>
              <p key={k.value} className="text-xl font-bold tabular-nums text-slate-900 leading-none animate-number-flip">{k.value}</p>
              <p className={`text-[10px] font-medium ${k.positive ? "text-emerald-600" : "text-red-500"}`}>{k.delta}</p>
            </div>
          ))}
        </div>
      </Card>

      {lastDiagnostic && (
        <MemoryHitBadge 
          mode={lastDiagnostic.mode}
          durationSeconds={lastDiagnostic.durationSeconds}
          confidence={lastDiagnostic.confidence}
        />
      )}

      {/* ── 2. BENTO GRID LAYOUT ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        {/* Main Column (Span 2) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Live Incidents */}
          <Card>
            <CardHeader className="border-b border-slate-100 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm font-semibold">Active Incidents</CardTitle>
                  <span className="flex items-center gap-1.5 text-[10px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
                    </span>
                    Monitoring Network
                  </span>
                </div>
                <Button variant="ghost" size="sm" className="h-7 text-xs text-slate-500" onClick={() => navigate("/incidents")}>
                  View all
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {incidents.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center bg-slate-50/50">
                  <span className="relative inline-flex mb-3">
                    <CheckCircle2 size={24} className="text-emerald-400 relative z-10" />
                    <span className="absolute inset-0 rounded-full bg-emerald-300/50" style={{animation: 'ringPulse 1.8s ease-out infinite'}} />
                  </span>
                  <p className="text-sm font-medium text-slate-700">Zero Active Incidents</p>
                  <p className="text-xs text-slate-400 mt-1">Platform is operating within normal parameters.</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent bg-slate-50/50">
                      <TableHead className="text-xs font-semibold h-8 w-8" />
                      <TableHead className="text-xs font-semibold h-8">Identifier</TableHead>
                      <TableHead className="text-xs font-semibold h-8">Impact</TableHead>
                      <TableHead className="text-xs font-semibold h-8">Status</TableHead>
                      <TableHead className="text-xs font-semibold h-8">Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {incidents.map(inc => (
                      <TableRow key={inc.id} className="cursor-pointer hover:bg-slate-50" onClick={() => setSelectedIncident(inc)}>
                        <TableCell className="py-2.5">
                          <span className={`block w-2 h-2 rounded-full ${severityDot(inc.severity)}`} />
                        </TableCell>
                        <TableCell className="py-2.5">
                          <span className="font-mono text-xs font-medium text-slate-700">{inc.id}</span>
                        </TableCell>
                        <TableCell className="py-2.5 max-w-[200px]">
                          <p className="text-xs text-slate-700 truncate">{inc.description}</p>
                        </TableCell>
                        <TableCell className="py-2.5">
                          <Badge variant={statusVariant(inc.status)} className="text-[10px]">{inc.status}</Badge>
                        </TableCell>
                        <TableCell className="py-2.5">
                          <span className="text-[11px] text-slate-400 tabular-nums">{timeAgo(inc.timestamp)}</span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Hindsight Memory */}
          <Card>
            <CardHeader className="border-b border-slate-100 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Brain size={14} className="text-indigo-500" />
                  <CardTitle className="text-sm font-semibold">Autonomous Resolutions</CardTitle>
                </div>
                <Button variant="ghost" size="sm" className="h-7 text-xs text-slate-500" onClick={() => navigate("/ai")}>
                  Browse Bank
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-slate-100">
              {memories.length === 0 ? (
                <div className="py-10 text-center text-xs text-slate-400 bg-slate-50/50">
                  No historical interventions logged.
                </div>
              ) : (
                memories.map((m, i) => (
                  <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                    <div className="min-w-0 pr-4">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[10px] font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">{m.incident_id}</span>
                        <span className="text-xs text-slate-700 truncate">{m.symptoms}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate leading-relaxed">
                        <span className="font-medium text-slate-600">Action taken:</span> {m.root_cause}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <Badge variant={m.outcome === "success" ? "success" : "destructive"} className="text-[10px] mb-1.5">
                        {m.outcome}
                      </Badge>
                      <div className="flex items-center gap-1.5 justify-end text-[10px] text-slate-400 font-mono">
                        {(m.success_rate * 100).toFixed(0)}% Conf
                        <div className="w-12 h-1 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-indigo-500 rounded-full animate-bar-grow" style={{ width: `${(m.success_rate ?? 1) * 100}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar Column (Span 1) */}
        <div className="space-y-4">
          
          {/* Health Status */}
          <Card>
            <CardHeader className="border-b border-slate-100 py-4">
              <div className="flex items-center gap-2">
                <Server size={14} className="text-slate-700" />
                <CardTitle className="text-sm font-semibold">Infrastructure Health</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {[
                { label: "Kubernetes Cluster", status: dash?.cluster_health ?? "Healthy", uptime: "99.99%" },
                { label: "Service Mesh", status: dash?.app_health ?? "Healthy", uptime: "99.97%" },
                { label: "Control Plane", status: dash?.platform_health ?? "Healthy", uptime: "100.0%" },
              ].map(row => (
                <div key={row.label} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">{row.label}</span>
                    <span className="text-[10px] font-mono text-slate-400">{row.uptime} SLA</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full animate-bar-grow ${row.status === 'Healthy' ? 'bg-emerald-500 w-full' : 'bg-amber-500 w-[95%]'}`} />
                    </div>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider ${row.status === 'Healthy' ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {row.status}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* System Telemetry (Replacing repetitive buttons) */}
          <Card>
            <CardHeader className="border-b border-slate-100 py-4 bg-slate-900 rounded-t-xl">
              <div className="flex items-center gap-2 text-white">
                <Activity size={14} className="text-emerald-400" />
                <CardTitle className="text-sm font-semibold">System Telemetry</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-0 bg-slate-900 rounded-b-xl text-slate-300 text-xs font-mono">
              <div className="p-4 border-b border-slate-800 space-y-2">
                <div className="flex justify-between"><span>CPU Allocation</span> <span key="42.1" className="text-white animate-number-flip">42.1%</span></div>
                <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-400 rounded-full w-[42%] animate-bar-grow" />
                </div>
              </div>
              <div className="p-4 border-b border-slate-800 space-y-2">
                <div className="flex justify-between"><span>Memory Usage</span> <span key="68.4" className="text-white animate-number-flip">68.4%</span></div>
                <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-400 rounded-full w-[68%] animate-bar-grow" />
                </div>
              </div>
              <div className="p-4 hover:bg-slate-800/50 transition-colors cursor-pointer flex items-center justify-between text-emerald-400" onClick={() => navigate("/audit")}>
                <span>View Full Audit Log</span>
                <ChevronRight size={12} />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Incident slide-over */}
      {selectedIncident && (
        <IncidentSheet incident={selectedIncident} onClose={() => setSelectedIncident(null)} />
      )}
    </div>
  );
};
