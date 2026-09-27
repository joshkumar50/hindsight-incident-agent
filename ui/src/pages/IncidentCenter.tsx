import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AlertTriangle, CheckCircle, Clock, RefreshCw, Flame, Zap, BrainCircuit } from 'lucide-react';
import MemoryHitBadge from '../components/MemoryHitBadge';
import { useStore } from '../store/useStore';

interface Incident {
  id: string; status: string; severity: string;
  start_time?: number; description: string;
  root_cause?: string; impacted_services?: string[];
}

const severityConfig: Record<string, { card: string; pill: string; dot: string; icon: string; bar: string }> = {
  Critical: {
    card: 'border-l-4 border-l-red-500 bg-red-50/40 border-red-200',
    pill: 'status-pill-red', dot: 'status-dot-red',
    icon: 'text-red-500',
    bar: 'bg-red-500',
  },
  High: {
    card: 'border-l-4 border-l-orange-500 bg-orange-50/40 border-orange-200',
    pill: 'status-pill-orange', dot: 'status-dot-orange',
    icon: 'text-orange-500',
    bar: 'bg-orange-500',
  },
  high: {
    card: 'border-l-4 border-l-orange-500 bg-orange-50/40 border-orange-200',
    pill: 'status-pill-orange', dot: 'status-dot-orange',
    icon: 'text-orange-500',
    bar: 'bg-orange-500',
  },
  Medium: {
    card: 'border-l-4 border-l-yellow-500 bg-yellow-50/40 border-yellow-200',
    pill: 'status-pill-yellow', dot: 'status-dot-yellow',
    icon: 'text-yellow-600',
    bar: 'bg-yellow-500',
  },
};

const getSeverityCfg = (s: string) =>
  severityConfig[s] ?? {
    card: 'border-l-4 border-l-slate-300 bg-white border-slate-200',
    pill: 'status-pill-slate', dot: 'status-dot-slate',
    icon: 'text-slate-400',
    bar: 'bg-slate-400',
  };

export const IncidentCenter = () => {
  const { data, isLoading, error, dataUpdatedAt } = useQuery<Incident[]>({
    queryKey: ['incidents'],
    queryFn: async () => { const res = await apiClient.get('/incidents'); return res.data; },
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  const lastDiagnostic = useStore((s) => s.lastDiagnostic);

  const incidents = Array.isArray(data) ? data : [];
  const activeIncidents = incidents.filter(i => i.status !== 'resolved' && i.status !== 'Resolved');

  return (
    <div className="space-y-4 max-w-4xl mx-auto">

      {/* Last Diagnostic Memory Card */}
      {lastDiagnostic && (
        <div className="premium-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-purple-50 flex items-center justify-center">
                <BrainCircuit size={12} className="text-purple-600" />
              </div>
              <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Last Diagnostic</span>
            </div>
            <span className="text-xs text-[var(--color-text-muted)]">
              {new Date(lastDiagnostic.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] italic truncate">
            &ldquo;{lastDiagnostic.query}&rdquo;
          </p>
          <MemoryHitBadge
            mode={lastDiagnostic.mode}
            durationSeconds={lastDiagnostic.durationSeconds}
            confidence={lastDiagnostic.confidence}
            incidentId={lastDiagnostic.incidentId}
          />
        </div>
      )}
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
          <RefreshCw size={12} className={isLoading ? 'animate-spin text-indigo-500' : ''} />
          {dataUpdatedAt
            ? `Last updated ${new Date(dataUpdatedAt).toLocaleTimeString()}`
            : 'Connecting...'}
        </div>
        <div className="flex items-center gap-2">
          {activeIncidents.length > 0 ? (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-red-700 bg-red-50 px-3 py-1.5 rounded-full border border-red-200 animate-pulse">
              <Flame size={11} /> {activeIncidents.length} active incident{activeIncidents.length !== 1 ? 's' : ''}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live — No Active Incidents
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="premium-card border-red-200 bg-red-50 p-4 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle size={14} className="text-red-500 shrink-0" />
          Failed to connect to Incident Engine.
        </div>
      )}

      {!error && !isLoading && incidents.length === 0 && (
        <div className="premium-card p-6 flex flex-col gap-4 border-emerald-200 bg-emerald-50/60">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center shrink-0">
              <CheckCircle size={20} className="text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-800">All Systems Operational</p>
              <p className="text-xs text-emerald-600 mt-0.5">
                No active incidents detected. Launch a Chaos experiment to see this section come alive.
              </p>
            </div>
          </div>
          <div className="pt-3 border-t border-emerald-200/60 flex items-center gap-2 text-[11px] font-medium text-emerald-700 font-mono uppercase tracking-wider">
            Last incident: 2h ago · MTTR last 24h: 8.3s
          </div>
        </div>
      )}

      {incidents.length > 0 && (
        <div className="space-y-3">
          {incidents.map((incident, idx) => {
            const cfg = getSeverityCfg(incident.severity);
            return (
              <div key={idx} className={`premium-card border rounded-xl p-5 transition-all ${cfg.card}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <AlertTriangle size={16} className={`${cfg.icon} mt-0.5 shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-[var(--color-text-primary)] font-mono">{incident.id}</p>
                      <p className="text-sm text-[var(--color-text-secondary)] mt-1 leading-relaxed">{incident.description}</p>
                      {incident.root_cause && (
                        <p className="text-xs text-[var(--color-text-muted)] mt-2 bg-white/70 border border-[var(--color-border)] rounded-md px-2 py-1 inline-block">
                          Root cause: <span className="font-mono font-medium text-[var(--color-text-primary)]">{incident.root_cause}</span>
                        </p>
                      )}
                      {incident.impacted_services && incident.impacted_services.length > 0 && (
                        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                          <Zap size={11} className="text-orange-400" />
                          {incident.impacted_services.map((svc, i) => (
                            <span key={i} className="text-xs font-mono bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded border border-orange-200">
                              {svc}
                            </span>
                          ))}
                        </div>
                      )}
                      {incident.start_time && (
                        <div className="flex items-center gap-1.5 mt-2">
                          <Clock size={11} className="text-[var(--color-text-muted)]" />
                          <span className="text-xs text-[var(--color-text-muted)]">
                            Started: {new Date(incident.start_time * 1000).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 shrink-0 items-end">
                    <span className={cfg.pill}>
                      <span className={cfg.dot}></span> {incident.severity}
                    </span>
                    <span className="status-pill-slate capitalize">
                      <span className="status-dot-slate"></span> {incident.status}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {isLoading && !data && (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="premium-card rounded-xl p-5 animate-pulse h-24" />
          ))}
        </div>
      )}
    </div>
  );
};
