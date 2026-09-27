import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Server, Box, Layers, Cpu, CheckCircle, XCircle, ChevronDown } from 'lucide-react';

interface Service { name: string; type: string; namespace: string; status: string; }
interface ClusterData {
  total_nodes: number; total_pods: number;
  namespaces: number; deployments: number;
  services: Service[];
}

const Stat = ({ label, value, icon: Icon }: {
  label: string; value: number; icon: React.ElementType;
}) => (
  <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-3 hover:shadow-md">
    <div className="flex items-center gap-2">
      <Icon size={14} className="text-slate-400" />
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
    </div>
    <div>
      <p className="text-3xl font-bold text-slate-900 tracking-tight font-num">{value}</p>
    </div>
  </div>
);

export const ClusterView = () => {
  const { data, isLoading, error } = useQuery<ClusterData>({
    queryKey: ['cluster'],
    queryFn: async () => { const res = await apiClient.get('/cluster'); return res.data; }
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse h-20"></div>
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
            <Stat label="Nodes" value={data.total_nodes} icon={Cpu} />
            <Stat label="Pods" value={data.total_pods} icon={Box} />
            <Stat label="Namespaces" value={data.namespaces} icon={Layers} />
            <Stat label="Deployments" value={data.deployments} icon={Server} />
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">Services in incident-agent-system</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white/95 backdrop-blur border-b border-slate-200 z-10">
                <tr>
                  {['Service', 'Namespace', 'Type', 'Status'].map(h => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                      <div className="flex items-center gap-1.5">
                        {h} <ChevronDown size={12} className="text-slate-300" />
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.services?.map((svc, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors border-b border-slate-100 last:border-0">
                    <td className="px-5 py-3 font-id">{svc.name}</td>
                    <td className="px-5 py-3 text-slate-500 font-num">{svc.namespace}</td>
                    <td className="px-5 py-3 text-slate-500">{svc.type}</td>
                    <td className="px-5 py-3">
                      {svc.status === 'Running' ? (
                        <span className="status-pill-emerald">
                          <span className="status-dot-emerald"></span> Running
                        </span>
                      ) : (
                        <span className="status-pill-red">
                          <span className="status-dot-red"></span> {svc.status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
