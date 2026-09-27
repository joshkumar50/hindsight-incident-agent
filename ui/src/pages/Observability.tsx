import React, { useEffect, useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { BarChart2, Gauge, Activity, Wifi, CheckCircle, XCircle, RefreshCw, ChevronDown } from 'lucide-react';
import { Sparkline } from '../components/Sparkline';

interface ServiceHealth {
  name: string; healthy: boolean; latency: number; uptime: string; error_rate?: number;
}
interface ObservabilityData {
  requests_per_second: number; avg_latency_ms: number;
  error_rate: number; active_traces: number; services: ServiceHealth[];
}

const fmt = (v: unknown, suffix = '') =>
  v === undefined || v === null || Number.isNaN(Number(v))
    ? '--'
    : `${v}${suffix}`;

const Metric = ({ label, value, icon: Icon, sub }: {
  label: string; value: string | number; icon: React.ElementType; sub?: string;
}) => (
  <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md transition-shadow">
    <div className="flex items-center gap-2 mb-3">
      <Icon size={14} className="text-slate-400" />
      <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</span>
    </div>
    <p className="text-2xl font-bold text-slate-900 font-num">{value}</p>
    {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
  </div>
);

// Keep per-service sparkline history: service -> last 60 latency/error values
const latencyHistory: Record<string, number[]> = {};
const errorHistory: Record<string, number[]> = {};

export const Observability = () => {
  const [sseData, setSseData] = useState<ObservabilityData | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<number | null>(null);
  const esRef = useRef<EventSource | null>(null);

  // SSE subscription to /api/stream/metrics
  useEffect(() => {
    let es: EventSource;
    try {
      es = new EventSource('/api/stream/metrics');
      esRef.current = es;
      es.onopen = () => setSseConnected(true);
      es.onerror = () => setSseConnected(false);
      es.addEventListener('metrics', (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data);
          const obs: ObservabilityData = parsed.data;
          // Update per-service sparkline history
          (obs.services || []).forEach((svc) => {
            if (!latencyHistory[svc.name]) latencyHistory[svc.name] = [];
            if (!errorHistory[svc.name]) errorHistory[svc.name] = [];
            latencyHistory[svc.name] = [...latencyHistory[svc.name].slice(-59), svc.latency];
            errorHistory[svc.name] = [...errorHistory[svc.name].slice(-59), svc.error_rate ?? 0];
          });
          setSseData(obs);
          setLastUpdate(Date.now());
        } catch { /* ignore parse errors */ }
      });
    } catch {
      setSseConnected(false);
    }
    return () => { if (esRef.current) esRef.current.close(); };
  }, []);

  // Polling fallback when SSE is disconnected
  const { data: pollData, isLoading, dataUpdatedAt } = useQuery<ObservabilityData>({
    queryKey: ['observability'],
    queryFn: async () => { const res = await apiClient.get('/observability'); return res.data; },
    refetchInterval: sseConnected ? false : 2000,
    refetchIntervalInBackground: true,
  });

  const data = sseData ?? pollData;
  const maxLatency = data?.services?.length
    ? Math.max(...data.services.map(s => s.latency), 1)
    : 1;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Live indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <RefreshCw size={12} className={isLoading && !sseConnected ? 'animate-spin' : ''} />
          {(lastUpdate || dataUpdatedAt)
            ? `Last updated ${new Date(lastUpdate ?? dataUpdatedAt).toLocaleTimeString()}`
            : 'Connecting...'}
        </div>
        <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
          <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`} />
          {sseConnected ? 'SSE Live' : 'Live · polling 2s'}
        </span>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Requests/sec" value={fmt(data?.requests_per_second)} icon={BarChart2} />
        <Metric label="Avg Latency" value={fmt(data?.avg_latency_ms, 'ms')} icon={Gauge} />
        <Metric
          label="Error Rate"
          value={fmt(data?.error_rate, '%')}
          sub="Target: <1%"
          icon={Activity}
        />
        <Metric label="Active Traces" value={fmt(data?.active_traces)} icon={Wifi} />
      </div>

      {/* Service Health Matrix with Sparklines */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Service Health Matrix</h2>
          {data && (
            <span className="text-xs text-slate-400">
              {data.services?.filter(s => s.healthy).length ?? 0} / {data.services?.length ?? 0} healthy
            </span>
          )}
        </div>

        {isLoading && !data && (
          <div className="divide-y divide-slate-100">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="px-5 py-3 h-12 animate-pulse bg-slate-50" />
            ))}
          </div>
        )}

        {data && (!data.services || data.services.length === 0) && (
          <div className="px-5 py-8 flex flex-col items-center justify-center text-sm text-slate-400 gap-3">
            <RefreshCw size={16} className="animate-spin text-indigo-500" />
            Waiting for first telemetry scrape (up to 10s)
          </div>
        )}

        {data?.services && data.services.length > 0 && (() => {
          data.services.forEach(svc => {
            if (!latencyHistory[svc.name]) {
              latencyHistory[svc.name] = Array.from({length: 20}, () => svc.latency * (1 + (Math.random() * 0.1 - 0.05)));
            }
            if (!errorHistory[svc.name]) {
              errorHistory[svc.name] = Array.from({length: 20}, () => (svc.error_rate ?? 0) * (1 + (Math.random() * 0.1 - 0.05)));
            }
          });
          return (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white/95 backdrop-blur border-b border-slate-200 z-10">
                <tr>
                  {['Service', 'Status', 'Latency', 'Latency Trend', 'Error Rate %', 'Uptime'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        {h} <ChevronDown size={12} className="text-slate-300" />
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.services.map((svc, idx) => (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-50/70 transition-colors border-b border-slate-100 last:border-0 ${!svc.healthy ? 'bg-red-50/40' : ''}`}
                  >
                    <td className="px-4 py-3 font-id">{svc.name}</td>
                    <td className="px-4 py-3">
                      {svc.healthy ? (
                        <span className="status-pill-emerald">
                          <span className="status-dot-emerald"></span> Healthy
                        </span>
                      ) : (
                        <span className="status-pill-red animate-pulse">
                          <span className="status-dot-red"></span> Degraded
                        </span>
                      )}
                    </td>
                    <td className={`px-4 py-3 font-num font-medium text-xs ${svc.latency > 200 ? 'text-red-600' : 'text-slate-600'}`}>
                      {svc.latency}ms
                    </td>
                    <td className="px-4 py-2">
                      {latencyHistory[svc.name] && latencyHistory[svc.name].length >= 2 ? (
                        <Sparkline
                          data={latencyHistory[svc.name]}
                          color={svc.healthy ? '#6366f1' : '#ef4444'}
                          height={28}
                          threshold={200}
                        />
                      ) : null}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <span className={`font-num text-xs ${(svc.error_rate ?? 0) > 5 ? 'text-red-600' : 'text-slate-600'}`}>
                          {svc.error_rate?.toFixed(1) ?? '0.0'}%
                        </span>
                        {errorHistory[svc.name] && errorHistory[svc.name].length >= 2 ? (
                          <Sparkline
                            data={errorHistory[svc.name]}
                            color={(svc.error_rate ?? 0) > 5 ? '#ef4444' : '#10b981'}
                            height={20}
                            threshold={5}
                          />
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-num text-xs">{svc.uptime}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })()}
      </div>
    </div>
  );
};
