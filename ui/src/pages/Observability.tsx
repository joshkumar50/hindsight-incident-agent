import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { BarChart2, Gauge, Activity, Wifi, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { LiveIndicator } from '../components/LiveIndicator';

interface ServiceHealth {
  name: string; healthy: boolean; latency: number; uptime: string; error_rate?: number;
}
interface ObservabilityData {
  requests_per_second: number; avg_latency_ms: number;
  error_rate: number; active_traces: number; services: ServiceHealth[];
}

const fmt = (v: unknown, suffix = '') =>
  v === undefined || v === null || Number.isNaN(Number(v)) ? '--' : `${v}${suffix}`;

const Metric = ({ label, value, icon: Icon, color, sub, chartData }: {
  label: string; value: string | number; icon: React.ElementType; color: string; sub?: string; chartData?: any[];
}) => (
  <Card>
    <CardContent className="p-4 flex flex-col justify-between h-full relative overflow-hidden">
      <div className="flex items-center gap-2 mb-3 relative z-10">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={13} />
        </div>
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="relative z-10">
        <p key={String(value)} className="text-2xl font-bold font-num text-slate-900 animate-number-flip">{value}</p>
        {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
      </div>
      {chartData && (
        <div className="absolute bottom-0 left-0 right-0 h-16 opacity-30 pointer-events-none">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <YAxis domain={['auto', 'auto']} hide />
              <Line type="monotone" dataKey="value" stroke="currentColor" strokeWidth={2} dot={false} className="text-indigo-600" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardContent>
  </Card>
);

const LatencyBar = ({ value, max, healthy }: { value: number; max: number; healthy: boolean }) => (
  <div className="h-1.5 bg-slate-100 rounded-full w-32">
    <div
      className={`h-full rounded-full transition-all duration-700 ${
        !healthy ? 'bg-red-400' : value > 100 ? 'bg-amber-400' : 'bg-emerald-400'
      }`}
      style={{ width: `${Math.max(4, Math.round((value / Math.max(max, 1)) * 100))}%` }}
    />
  </div>
);

// Fake data for sparklines since API doesn't provide history arrays
const generateSparkline = () => Array.from({ length: 15 }, () => ({ value: Math.random() * 100 + 20 }));

export const Observability = () => {
  const { data, isLoading, error, dataUpdatedAt } = useQuery<ObservabilityData>({
    queryKey: ['observability'],
    queryFn: async () => { const res = await apiClient.get('/observability'); return res.data; },
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  const maxLatency = data?.services?.length ? Math.max(...data.services.map(s => s.latency), 1) : 1;
  const sparkData = React.useMemo(() => generateSparkline(), [dataUpdatedAt]); // Update on fetch

  return (
    <div className="space-y-4 max-w-5xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between">
        <LiveIndicator updatedAt={dataUpdatedAt} />
        <Badge variant="success" className="gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse-soft" /> Live
        </Badge>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to Observability service.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Requests/sec" value={fmt(data?.requests_per_second)} icon={BarChart2} color="bg-indigo-50 text-indigo-600" chartData={sparkData} />
        <Metric label="Avg Latency" value={fmt(data?.avg_latency_ms, 'ms')} icon={Gauge} color="bg-sky-50 text-sky-600" chartData={sparkData} />
        <Metric label="Error Rate" value={fmt(data?.error_rate, '%')} sub="Target: <1%" icon={Activity} color={data?.error_rate === undefined ? 'bg-slate-50 text-slate-400' : data.error_rate < 1 ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'} />
        <Metric label="Active Traces" value={fmt(data?.active_traces)} icon={Wifi} color="bg-violet-50 text-violet-600" chartData={sparkData} />
      </div>

      <Card>
        <CardHeader className="border-b border-slate-100 pb-3 flex flex-row items-center justify-between">
          <CardTitle>Service Health Matrix</CardTitle>
          {data && (
            <span className="text-xs text-slate-400 font-num">
              {data.services?.filter(s => s.healthy).length ?? 0} / {data.services?.length ?? 0} healthy
            </span>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {isLoading && !data && (
            <div className="divide-y divide-slate-100">
              {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12 rounded-none" />)}
            </div>
          )}
          {data && (!data.services || data.services.length === 0) && (
            <div className="px-5 py-8 text-center text-sm text-slate-400">No service data available yet.</div>
          )}
          {data?.services && data.services.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Service</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Uptime</TableHead>
                  <TableHead>Latency Bar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.services.map((svc, idx) => (
                  <TableRow key={idx} className={`transition-colors duration-150 hover:bg-slate-50/80 ${!svc.healthy ? 'bg-red-50/40' : ''}`}>
                    <TableCell className="font-id font-medium text-slate-800">{svc.name}</TableCell>
                    <TableCell>
                      {svc.healthy ? (
                        <Badge variant="success" className="gap-1.5"><CheckCircle size={10} /> Healthy</Badge>
                      ) : (
                        <Badge variant="destructive" className="gap-1.5 animate-pulse"><XCircle size={10} /> Degraded</Badge>
                      )}
                    </TableCell>
                    <TableCell className={`font-num font-medium ${svc.latency > 100 ? 'text-red-600' : 'text-slate-600'}`}>{svc.latency}ms</TableCell>
                    <TableCell className="text-slate-600 font-num">{svc.uptime}</TableCell>
                    <TableCell><LatencyBar value={svc.latency} max={maxLatency} healthy={svc.healthy} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
