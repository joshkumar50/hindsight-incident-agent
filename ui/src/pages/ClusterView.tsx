import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Server, Box, Layers, Cpu, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface Service { name: string; type: string; namespace: string; status: string; }
interface ClusterData {
  total_nodes: number; total_pods: number;
  namespaces: number; deployments: number;
  services: Service[];
}

const Stat = ({ label, value, icon: Icon, color }: {
  label: string; value: number; icon: React.ElementType; color: string;
}) => (
  <Card>
    <CardContent className="p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold font-num text-slate-900">{value}</p>
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</p>
      </div>
    </CardContent>
  </Card>
);

export const ClusterView = () => {
  const { data, isLoading, error } = useQuery<ClusterData>({
    queryKey: ['cluster'],
    queryFn: async () => { const res = await apiClient.get('/cluster'); return res.data; }
  });

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Cannot connect to Cluster API -- is the dashboard-bff running?
        </div>
      )}
      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Nodes" value={data.total_nodes} icon={Cpu} color="bg-indigo-50 text-indigo-600" />
            <Stat label="Pods" value={data.total_pods} icon={Box} color="bg-violet-50 text-violet-600" />
            <Stat label="Namespaces" value={data.namespaces} icon={Layers} color="bg-sky-50 text-sky-600" />
            <Stat label="Deployments" value={data.deployments} icon={Server} color="bg-emerald-50 text-emerald-600" />
          </div>

          <Card>
            <CardHeader className="border-b border-slate-100 pb-3">
              <CardTitle>Services in incident-agent-system</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Service</TableHead>
                    <TableHead>Namespace</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.services?.map((svc, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-id font-medium text-slate-800">{svc.name}</TableCell>
                      <TableCell className="text-slate-500">{svc.namespace}</TableCell>
                      <TableCell className="text-slate-500">{svc.type}</TableCell>
                      <TableCell>
                        {svc.status === 'Running' ? (
                          <Badge variant="success" className="gap-1.5">
                            <CheckCircle size={10} /> Running
                          </Badge>
                        ) : (
                          <Badge variant="destructive" className="gap-1.5">
                            <XCircle size={10} /> {svc.status}
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};
