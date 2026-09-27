import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Clock, ShieldCheck, TrendingDown, AlertTriangle } from 'lucide-react';

interface RecoveryData {
  total_experiments: number; successful_recoveries: number;
  average_mttr_seconds: number; active_incidents: Record<string, unknown>;
}

export const RecoveryCenter = () => {
  const { data, isLoading, error } = useQuery<RecoveryData>({
    queryKey: ['recovery'],
    queryFn: async () => { const res = await apiClient.get('/recovery'); return res.data; }
  });

  const activeCount = data ? Object.keys(data.active_incidents || {}).length : 0;
  const successRate = data && data.total_experiments > 0
    ? Math.round((data.successful_recoveries / data.total_experiments) * 100)
    : 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse h-24" />
          ))}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to Recovery Validation Service.
        </div>
      )}
      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 bg-indigo-50 rounded-lg flex items-center justify-center">
                  <TrendingDown size={13} className="text-indigo-600" />
                </div>
                <span className="text-xs text-slate-500 font-medium">Experiments</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{data.total_experiments}</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 bg-emerald-50 rounded-lg flex items-center justify-center">
                  <ShieldCheck size={13} className="text-emerald-600" />
                </div>
                <span className="text-xs text-slate-500 font-medium">Recoveries</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{data.successful_recoveries}</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 bg-sky-50 rounded-lg flex items-center justify-center">
                  <Clock size={13} className="text-sky-600" />
                </div>
                <span className="text-xs text-slate-500 font-medium">Avg MTTR</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{(data.average_mttr_seconds || 0).toFixed(1)}s</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md">
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${activeCount > 0 ? 'bg-red-50' : 'bg-emerald-50'}`}>
                  <AlertTriangle size={13} className={activeCount > 0 ? 'text-red-600' : 'text-emerald-600'} />
                </div>
                <span className="text-xs text-slate-500 font-medium">Active Incidents</span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{activeCount}</p>
            </div>
          </div>

          {/* Success rate bar */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-slate-900">Recovery Success Rate</p>
              <p className="text-sm font-bold text-emerald-700">{successRate}%</p>
            </div>
            <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-700"
                style={{ width: `${successRate}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 mt-2">
              {data.successful_recoveries} successful out of {data.total_experiments} total experiments
            </p>
          </div>
        </>
      )}
    </div>
  );
};
