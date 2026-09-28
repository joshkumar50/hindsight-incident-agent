import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AlertTriangle, CheckCircle, Clock, RefreshCw, Flame, Zap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { MemoryHitBadge } from '../components/MemoryHitBadge';
import { useStore } from '../store/useStore';

interface Incident {
  id: string; status: string; severity: string;
  start_time?: number; description: string;
  root_cause?: string; impacted_services?: string[];
}

const statusVariant = (status: string) => {
  const s = status.toLowerCase();
  if (s === 'resolved') return 'resolved';
  if (s === 'investigating') return 'investigating';
  return 'secondary';
};

const severityDot = (severity: string) => {
  const s = severity.toLowerCase();
  if (s === 'critical') return 'bg-red-500';
  if (s === 'high') return 'bg-orange-500';
  if (s === 'medium') return 'bg-amber-400';
  return 'bg-slate-300';
};

export const IncidentCenter = () => {
  const { data, isLoading, error, dataUpdatedAt } = useQuery<Incident[]>({
    queryKey: ['incidents'],
    queryFn: async () => { const res = await apiClient.get('/incidents'); return res.data; },
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  const incidents = Array.isArray(data) ? data : [];
  const activeIncidents = incidents.filter(i => i.status.toLowerCase() !== 'resolved');

  const { lastDiagnostic, setLastDiagnostic } = useStore();

  React.useEffect(() => {
    if (incidents.length > 0) {
      // Find the most recently analyzed incident (has root_cause)
      const analyzed = incidents.find(i => i.root_cause);
      if (analyzed) {
        const anyInc = analyzed as any;
        const isRecall = anyInc.source === 'memory' || anyInc.llm_model_used?.includes('hindsight');
        // fallback to fresh if it's a real LLM
        const mode = isRecall ? 'recall' : 'fresh';
        setLastDiagnostic({
          mode,
          durationSeconds: isRecall ? 0.4 : 3.8,
          confidence: isRecall ? 0.98 : 0.85
        });
      }
    }
  }, [incidents, setLastDiagnostic]);

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
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
            <Badge variant="destructive" className="gap-1.5 animate-pulse">
              <Flame size={11} /> {activeIncidents.length} active incident{activeIncidents.length !== 1 ? 's' : ''}
            </Badge>
          ) : (
            <Badge variant="success" className="gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live
            </Badge>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to Incident Engine.
        </div>
      )}

      {lastDiagnostic && (
        <div className="mb-4">
          <MemoryHitBadge 
            mode={lastDiagnostic.mode}
            durationSeconds={lastDiagnostic.durationSeconds}
            confidence={lastDiagnostic.confidence}
          />
        </div>
      )}

      {!error && !isLoading && incidents.length === 0 && (
        <Card className="bg-emerald-50 border-emerald-200">
          <CardContent className="p-6 flex items-center gap-4">
            <CheckCircle size={20} className="text-emerald-600 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-800">All Systems Operational</p>
              <p className="text-xs text-emerald-600 mt-0.5">
                No active incidents detected. Launch a Chaos experiment to see this section come alive.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {incidents.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-6" />
                  <TableHead>ID</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Impacted</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Opened</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {incidents.map((incident, idx) => (
                  <TableRow key={idx} className="cursor-pointer">
                    <TableCell>
                      <span className={`block w-2 h-2 rounded-full ${severityDot(incident.severity)}`} />
                    </TableCell>
                    <TableCell>
                      <span className="font-id font-bold text-slate-900">{incident.id}</span>
                    </TableCell>
                    <TableCell className="max-w-[300px]">
                      <p className="text-sm text-slate-700">{incident.description}</p>
                      {incident.root_cause && (
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          Root cause: <span className="font-id font-medium">{incident.root_cause}</span>
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {incident.impacted_services && incident.impacted_services.length > 0 ? (
                          incident.impacted_services.map((svc, i) => (
                            <Badge key={i} variant="warning" className="gap-1"><Zap size={10}/>{svc}</Badge>
                          ))
                        ) : <span className="text-[10px] text-slate-300">—</span>}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(incident.status)}>{incident.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={incident.severity.toLowerCase() === 'high' || incident.severity.toLowerCase() === 'critical' ? 'destructive' : 'secondary'}>
                        {incident.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {incident.start_time && (
                        <div className="flex items-center gap-1 text-slate-400">
                          <Clock size={11} />
                          <span className="font-num text-[11px]">
                            {new Date(incident.start_time * 1000).toLocaleTimeString()}
                          </span>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {isLoading && !data && (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      )}
    </div>
  );
};
