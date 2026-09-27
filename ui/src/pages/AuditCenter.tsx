import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { ClipboardList, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface AuditLog {
  timestamp: string; event_type: string; incident_id?: string;
  decision?: string; confidence_score?: number; human_approved?: boolean;
}

const eventVariant = (type: string) => {
  if (type.includes('REMEDIATION') || type.includes('RECOVERY')) return 'success';
  if (type.includes('INCIDENT') || type.includes('ALERT')) return 'destructive';
  if (type.includes('CHAOS')) return 'warning';
  return 'default';
};

export const AuditCenter = () => {
  const { data, isLoading, error } = useQuery<AuditLog[]>({
    queryKey: ['audit'],
    queryFn: async () => { const res = await apiClient.get('/audit'); return res.data; }
  });

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      {isLoading && <Skeleton className="h-48 w-full" />}
      
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to Audit Engine.
        </div>
      )}

      {data && data.length === 0 && (
        <Card className="bg-slate-50 border-slate-200">
          <CardContent className="p-6 flex items-center gap-4">
            <ClipboardList size={20} className="text-slate-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-slate-700">No audit events recorded</p>
              <p className="text-xs text-slate-500 mt-0.5">Events will appear here as the platform takes autonomous actions.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {data && data.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-100">
            <CardTitle className="text-sm flex items-center gap-2">
              <ClipboardList size={15} className="text-indigo-600" /> Decision Audit Trail
            </CardTitle>
            <span className="text-xs font-num text-slate-400">{data.length} events</span>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Incident ID</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Approved</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((log, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-num text-slate-500 whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '--'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={eventVariant(log.event_type || '') as any}>
                        {log.event_type || '--'}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-id text-slate-600">{log.incident_id || '--'}</TableCell>
                    <TableCell className="text-slate-600">{log.decision || '--'}</TableCell>
                    <TableCell>
                      {log.confidence_score != null ? (
                        <Badge variant={log.confidence_score >= 0.9 ? 'success' : log.confidence_score >= 0.7 ? 'warning' : 'destructive'}>
                          {(log.confidence_score * 100).toFixed(0)}%
                        </Badge>
                      ) : '--'}
                    </TableCell>
                    <TableCell>
                      {log.human_approved ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                          <CheckCircle size={11} /> Yes
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">Auto</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
