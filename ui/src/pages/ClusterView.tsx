import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Server, Box, Layers, Cpu, CheckCircle, XCircle } from 'lucide-react';

interface Service { name: string; type: string; namespace: string; status: string; }
interface ClusterData {
  total_nodes: number; total_pods: number;
  namespaces: number; deployments: number;
  services: Service[];
}

const Stat = ({ label, value, icon: Icon, color }: {
  label: string; value: number; icon: React.ElementType; color: string;
}) => (
  <div className="bg-white border border-slate-200 rounded-xl p-5 flex items-center gap-4 hover:shadow-md">
    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
      <Icon size={18} />
    </div>
    <div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 font-medium">{label}</p>
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
            <Stat label="Nodes" value={data.total_nodes} icon={Cpu} color="bg-indigo-50 text-indigo-600" />
            <Stat label="Pods" value={data.total_pods} icon={Box} color="bg-violet-50 text-violet-600" />
            <Stat label="Namespaces" value={data.namespaces} icon={Layers} color="bg-sky-50 text-sky-600" />
            <Stat label="Deployments" value={data.deployments} icon={Server} color="bg-emerald-50 text-emerald-600" />
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">Services in incident-agent-system</h2>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50">
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Service</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Namespace</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.services?.map((svc, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-5 py-3 font-mono text-slate-800 font-medium">{svc.name}</td>
                    <td className="px-5 py-3 text-slate-500">{svc.namespace}</td>
                    <td className="px-5 py-3 text-slate-500">{svc.type}</td>
                    <td className="px-5 py-3">
                      {svc.status === 'Running' ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                          <CheckCircle size={10} /> Running
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-red-700 bg-red-50 px-2 py-0.5 rounded-full">
                          <XCircle size={10} /> {svc.status}
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
