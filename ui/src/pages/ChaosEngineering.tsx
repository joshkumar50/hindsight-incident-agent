import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Zap, CheckCircle, AlertTriangle, Play, Square } from 'lucide-react';

interface Experiment { scenario_id: string; target_service: string; }
interface ChaosData { active_experiments: Record<string, Experiment>; error?: string; }

const scenarios = [
  { id: '1', name: 'Database Lock', risk: 'medium' },
  { id: '2', name: 'CPU Spike', risk: 'low' },
  { id: '3', name: 'Memory Leak', risk: 'medium' },
  { id: '4', name: 'Network Latency', risk: 'low' },
  { id: '5', name: 'Packet Loss', risk: 'medium' },
  { id: '6', name: 'CrashLoopBackOff', risk: 'high' },
  { id: '7', name: 'Pod Crash', risk: 'high' },
  { id: '8', name: 'Deployment Failure', risk: 'high' },
  { id: '9', name: 'Replica Failure', risk: 'medium' },
  { id: '10', name: 'Node Drain Simulation', risk: 'high' },
  { id: '11', name: 'Redis Failure', risk: 'medium' },
  { id: '12', name: 'API Gateway Failure', risk: 'high' },
  { id: '13', name: 'High Error Rate', risk: 'medium' },
  { id: '14', name: 'Slow Database Queries', risk: 'low' },
  { id: '15', name: 'Cascading Failure', risk: 'high' },
];

const services = ['auth-service', 'payment-service', 'order-service', 'inventory-service', 'notification-service', 'all'];

const riskColor = (r: string) => {
  if (r === 'high') return 'text-red-600 bg-red-50';
  if (r === 'medium') return 'text-amber-600 bg-amber-50';
  return 'text-emerald-600 bg-emerald-50';
};

export const ChaosEngineering = () => {
  const queryClient = useQueryClient();
  const [selectedScenario, setSelectedScenario] = useState('1');
  const [targetService, setTargetService] = useState('auth-service');

  const { data, isLoading, error } = useQuery<ChaosData>({
    queryKey: ['chaos'],
    queryFn: async () => { const res = await apiClient.get('/chaos'); return res.data; }
  });

  const startMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/chaos/start', {
        scenario_id: selectedScenario,
        target_service: targetService,
        duration_seconds: 60
      });
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chaos'] })
  });

  const stopMutation = useMutation({
    mutationFn: async (experimentId: string) => {
      const res = await apiClient.post(`/chaos/stop/${experimentId}`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chaos'] })
  });

  const selectedScenarioInfo = scenarios.find(s => s.id === selectedScenario);
  const activeCount = data ? Object.keys(data.active_experiments || {}).length : 0;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Launch panel */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-5">
          <Zap size={16} className="text-indigo-600" />
          <h2 className="text-sm font-semibold text-slate-900">Launch Experiment</h2>
          {selectedScenarioInfo && (
            <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full ${riskColor(selectedScenarioInfo.risk)}`}>
              {selectedScenarioInfo.risk.toUpperCase()} RISK
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Failure Scenario</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {scenarios.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Target Service</label>
            <select
              value={targetService}
              onChange={(e) => setTargetService(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {services.map(svc => (
                <option key={svc} value={svc}>{svc}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={() => startMutation.mutate()}
          disabled={startMutation.isPending || activeCount > 0}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play size={14} />
          {startMutation.isPending ? 'Launching...' : 'Launch Experiment'}
        </button>
        {startMutation.isSuccess && (
          <div className="mt-3 flex items-center gap-2 text-emerald-700 text-sm">
            <CheckCircle size={14} /> Experiment started successfully
          </div>
        )}
        {startMutation.isError && (
          <div className="mt-3 flex items-center gap-2 text-red-700 text-sm">
            <AlertTriangle size={14} /> Failed to start. Another experiment may already be active.
          </div>
        )}
      </div>

      {/* Active experiments */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-900">Active Experiments</h2>
            {activeCount > 0 && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">{activeCount} running</span>
            )}
          </div>
        </div>
        {isLoading && <div className="h-12 bg-slate-100 rounded-lg animate-pulse" />}
        {error && <p className="text-sm text-red-600">Chaos Controller unavailable.</p>}
        {data && !data.error && (
          activeCount === 0 ? (
            <div className="flex items-center gap-3 text-slate-500">
              <CheckCircle size={16} className="text-emerald-500" />
              <span className="text-sm">No active experiments -- system is stable</span>
            </div>
          ) : (
            <div className="space-y-3">
              {Object.entries(data.active_experiments).map(([id, exp]) => (
                <div key={id} className="flex items-center justify-between p-4 bg-amber-50 border border-amber-200 rounded-xl">
                  <div>
                    <p className="text-sm font-mono font-semibold text-slate-900">{id}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                       Scenario: <span className="font-medium">{scenarios.find(s => String(s.id) === String(exp.scenario_id))?.name ?? exp.scenario_id}</span> · Target: <span className="font-medium">{exp.target_service}</span>
                     </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1.5 text-xs font-medium text-amber-700 bg-amber-100 px-2.5 py-1 rounded-full">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                      Active
                    </span>
                    <button
                      onClick={() => stopMutation.mutate(id)}
                      disabled={stopMutation.isPending}
                      className="flex items-center gap-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 px-3 py-1.5 rounded-lg transition disabled:opacity-50"
                    >
                      <Square size={12} fill="currentColor" /> Stop
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
        {data?.error && <p className="text-sm text-red-600">{data.error}</p>}
      </div>
    </div>
  );
};
