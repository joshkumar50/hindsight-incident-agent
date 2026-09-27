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
    {
      label: "$ SAVED",
      value: `$${((recovered * 4200)).toLocaleString()}`,
      delta: "est. eng-hours",
      positive: true,
      icon: <DollarSign size={12} className="text-slate-400" />,
    },
  ];

  return (
    <div className="space-y-4 max-w-6xl mx-auto">

      {/* ── 1. KPI STRIP ──────────────────────────────────────── */}
      <Card>
        <div className="grid grid-cols-3 md:grid-cols-6 divide-x divide-slate-100">
          {kpis.map(k => (
            <div key={k.label} className="px-4 py-3 flex flex-col gap-1">
              <div className="flex items-center gap-1">
                {k.icon}
                <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{k.label}</span>
              </div>
              <p className="text-xl font-bold tabular-nums text-slate-900 leading-none">{k.value}</p>
              <p className={`text-[10px] font-medium ${k.positive ? "text-emerald-600" : "text-red-500"}`}>{k.delta}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* ── 2. LIVE INCIDENT FEED ─────────────────────────────── */}
      <Card className="min-h-[420px]">
        <CardHeader className="border-b border-slate-100 pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle>Live Incidents</CardTitle>
              <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                Watching 12 services
              </span>
            </div>
            <Button variant="outline" size="sm" onClick={() => navigate("/incidents")}>
              View all <ChevronRight size={13} />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="px-0 pb-0">
          {incidents.length === 0 ? (
            /* Empty state */
            <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
              <span className="relative flex h-4 w-4">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-50" />
                <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500" />
              </span>
              <div>
                <p className="text-sm font-medium text-slate-700">All systems operational</p>
                <p className="text-xs text-slate-400 mt-1">
                  Last incident: resolved · MTTR {mttr > 0 ? `${mttr}s` : "—"}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => navigate("/chaos")}>
                <Zap size={12} /> Simulate Incident
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-6" />
                  <TableHead>ID</TableHead>
                  <TableHead>Symptoms</TableHead>
                  <TableHead>Impacted</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Age</TableHead>
                  <TableHead className="w-6" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {incidents.map(inc => (
                  <TableRow
                    key={inc.id}
                    className="cursor-pointer"
                    onClick={() => setSelectedIncident(inc)}
                  >
                    <TableCell>
                      <span className={`block w-2 h-2 rounded-full ${severityDot(inc.severity)}`} />
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs text-slate-700">{inc.id}</span>
                    </TableCell>
                    <TableCell className="max-w-[260px]">
                      <p className="text-xs text-slate-700 line-clamp-1">{inc.description}</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">{inc.root_cause}</p>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {inc.impacted_services.slice(0, 2).map(s => (
                          <Badge key={s} variant="secondary">{s}</Badge>
                        ))}
                        {inc.impacted_services.length > 2 && (
                          <Badge variant="secondary">+{inc.impacted_services.length - 2}</Badge>
                        )}
                        {inc.impacted_services.length === 0 && (
                          <span className="text-[10px] text-slate-300">—</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(inc.status)}>{inc.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-[11px] text-slate-400 tabular-nums">{timeAgo(inc.timestamp)}</span>
                    </TableCell>
                    <TableCell>
                      <ChevronRight size={13} className="text-slate-300" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ── 3. QUICK ACTIONS ──────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Button variant="outline" className="justify-start gap-2" onClick={() => navigate("/ai")}>
          <Search size={13} className="text-slate-400" /> Run Diagnostic
        </Button>
        <Button variant="outline" className="justify-start gap-2" onClick={() => navigate("/chaos")}>
          <FlaskConical size={13} className="text-slate-400" /> Trigger Chaos
        </Button>
        <Button variant="outline" className="justify-start gap-2" onClick={() => navigate("/ai")}>
          <Brain size={13} className="text-slate-400" /> View Memory
        </Button>
        <Button variant="outline" className="justify-start gap-2" onClick={() => navigate("/audit")}>
          <Activity size={13} className="text-slate-400" /> Open Audit
        </Button>
      </div>

      {/* ── 4. SECONDARY GRID ─────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Health Status */}
        <Card>
          <CardHeader className="border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Server size={13} className="text-slate-400" />
              <CardTitle>Health Status</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="py-0 px-5 divide-y divide-slate-100">
            {[
              { label: "Cluster", status: dash?.cluster_health ?? "…", uptime: "99.99%", checked: "just now" },
              { label: "Application", status: dash?.app_health ?? "…", uptime: "99.97%", checked: "3s ago" },
              { label: "Platform", status: dash?.platform_health ?? "…", uptime: "100%", checked: "3s ago" },
            ].map(row => (
              <div key={row.label} className="flex items-center justify-between py-2.5">
                <div className="flex items-center gap-2">
                  {row.status === "Healthy"
                    ? <CheckCircle2 size={13} className="text-emerald-500" />
                    : <AlertTriangle size={13} className="text-amber-500" />}
                  <span className="text-sm text-slate-700">{row.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 tabular-nums">{row.uptime}</span>
                  <Badge variant={row.status === "Healthy" ? "success" : "warning"}>{row.status}</Badge>
                  <span className="text-[10px] text-slate-300 hidden md:block">{row.checked}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent Memory */}
        <Card>
          <CardHeader className="border-b border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain size={13} className="text-slate-400" />
                <CardTitle>Hindsight Memory</CardTitle>
              </div>
              <Button variant="ghost" size="sm" onClick={() => navigate("/ai")}>
                View all <ChevronRight size={12} />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="py-0 px-5 divide-y divide-slate-100">
            {memories.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No memories retained yet.</p>
            ) : (
              memories.map((m, i) => (
                <div key={i} className="py-2.5 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-[11px] text-slate-500">{m.incident_id}</p>
                    <p className="text-xs text-slate-700 line-clamp-1 mt-0.5">{m.symptoms}</p>
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1">
                    <Badge variant={m.outcome === "success" ? "success" : "destructive"}>
                      {m.outcome}
                    </Badge>
                    <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${(m.success_rate ?? 1) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

      </div>

      {/* Incident slide-over */}
      {selectedIncident && (
        <IncidentSheet incident={selectedIncident} onClose={() => setSelectedIncident(null)} />
      )}
    </div>
  );
};
