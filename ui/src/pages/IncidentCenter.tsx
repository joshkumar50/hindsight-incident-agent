import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AlertTriangle, CheckCircle, Clock, RefreshCw, Flame, Zap } from 'lucide-react';

interface Incident {
  id: string; status: string; severity: string;
  start_time?: number; description: string;
  root_cause?: string; impacted_services?: string[];
}

const severityConfig: Record<string, { card: string; badge: string; icon: string }> = {
  Critical: {
    card: 'border-red-300 bg-red-50/60',
    badge: 'bg-red-100 text-red-700 border-red-200',
    icon: 'text-red-500',
  },
  High: {
    card: 'border-orange-300 bg-orange-50/60',
    badge: 'bg-orange-100 text-orange-700 border-orange-200',
    icon: 'text-orange-500',
  },
  high: {
    card: 'border-orange-300 bg-orange-50/60',
    badge: 'bg-orange-100 text-orange-700 border-orange-200',
    icon: 'text-orange-500',
  },
  Medium: {
    card: 'border-yellow-200 bg-yellow-50/60',
    badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    icon: 'text-yellow-600',
  },
};

const getSeverityCfg = (s: string) =>
  severityConfig[s] ?? {
    card: 'border-slate-200 bg-white',
    badge: 'bg-slate-100 text-slate-600 border-slate-200',
    icon: 'text-slate-400',
  };

export const IncidentCenter = () => {
  const { data, isLoading, error, dataUpdatedAt } = useQuery<Incident[]>({
    queryKey: ['incidents'],
    queryFn: async () => { const res = await apiClient.get('/incidents'); return res.data; },
    refetchInterval: 3000, // Poll every 3 seconds so incidents appear within moments
    refetchIntervalInBackground: true,
  });

  const incidents = Array.isArray(data) ? data : [];
  const activeIncidents = incidents.filter(i => i.status !== 'resolved' && i.status !== 'Resolved');

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          {dataUpdatedAt
            ? `Last checked ${new Date(dataUpdatedAt).toLocaleTimeString()}`
            : 'Connecting...'}
        </div>
        <div className="flex items-center gap-2">
          {activeIncidents.length > 0 ? (
            <span className="flex items-center gap-1.5 text-xs font-medium text-red-700 bg-red-50 px-2.5 py-1 rounded-full border border-red-200 animate-pulse">
              <Flame size={11} /> {activeIncidents.length} active incident{activeIncidents.length !== 1 ? 's' : ''}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to Incident Engine.
        </div>
      )}

      {!error && !isLoading && incidents.length === 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 flex items-center gap-4">
          <CheckCircle size={20} className="text-emerald-600 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-emerald-800">All Systems Operational</p>
            <p className="text-xs text-emerald-600 mt-0.5">
              No active incidents detected. Launch a Chaos experiment to see this section come alive.
            </p>
          </div>
        </div>
      )}

      {incidents.length > 0 && (
        <div className="space-y-3">
          {incidents.map((incident, idx) => {
            const cfg = getSeverityCfg(incident.severity);
            return (
              <div
                key={idx}
                className={`border rounded-xl p-5 hover:shadow-md transition-shadow ${cfg.card}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={16} className={`${cfg.icon} mt-0.5 shrink-0`} />
                    <div>
                      <p className="text-sm font-bold text-slate-900 font-mono">{incident.id}</p>
                      <p className="text-sm text-slate-700 mt-1">{incident.description}</p>
                      {incident.root_cause && (
                        <p className="text-xs text-slate-500 mt-1">
                          Root cause: <span className="font-mono font-medium text-slate-700">{incident.root_cause}</span>
                        </p>
                      )}
                      {incident.impacted_services && incident.impacted_services.length > 0 && (
                        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                          <Zap size={11} className="text-orange-400" />
                          {incident.impacted_services.map((svc, i) => (
                            <span key={i} className="text-xs font-mono bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
                              {svc}
                            </span>
                          ))}
                        </div>
                      )}
                      {incident.start_time && (
                        <div className="flex items-center gap-1.5 mt-2">
                          <Clock size={11} className="text-slate-400" />
                          <span className="text-xs text-slate-400">
                            Started: {new Date(incident.start_time * 1000).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 shrink-0 items-end">
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${cfg.badge}`}>
                      {incident.severity}
                    </span>
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200 capitalize">
                      {incident.status}
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
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse h-24" />
          ))}
        </div>
      )}
    </div>
  );
};
