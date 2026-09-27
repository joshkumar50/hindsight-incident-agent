import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Zap, CheckCircle, AlertTriangle, Play, Square, Flame, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

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

const riskVariant = (r: string) => {
  if (r === 'high') return 'destructive';
  if (r === 'medium') return 'warning';
  return 'success';
};

export const ChaosEngineering = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selectedScenario, setSelectedScenario] = useState('1');
  const [targetService, setTargetService] = useState('auth-service');
  const [simToast, setSimToast] = useState<'idle' | 'success' | 'error'>('idle');

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

  const simulateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/chaos/start', {
        scenario_id: '7',
        target_service: 'order-service',
        duration_seconds: 60,
      });
      return res.data;
    },
    onSuccess: () => {
      setSimToast('success');
      queryClient.invalidateQueries({ queryKey: ['chaos'] });
      setTimeout(() => navigate('/incidents'), 1500);
    },
    onError: () => setSimToast('error'),
  });

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {/* ── QUICK ACTION: Simulate Incident ───────────────────────── */}
      <Card className="bg-gradient-to-r from-indigo-600 to-violet-600 border-none text-white shadow-lg">
        <CardContent className="p-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center shrink-0">
                <Flame size={20} className="text-white" />
              </div>
              <div>
                <h2 className="text-base font-bold leading-none">Simulate Incident →</h2>
                <p className="text-sm text-indigo-100 mt-1">
                  Inject a Pod Crash fault into <span className="font-id font-semibold">order-service</span>. Feeds the full SRE pipeline — chaos → anomaly → incident engine → AI heal → resolved.
                </p>
                {simToast === 'success' && (
                  <p className="mt-2 text-xs font-medium text-emerald-200 flex items-center gap-1.5">
                    <CheckCircle size={12} /> Incident injected! Navigating to Incident Center…
                  </p>
                )}
                {simToast === 'error' && (
                  <p className="mt-2 text-xs font-medium text-red-200 flex items-center gap-1.5">
                    <AlertTriangle size={12} /> Failed — another experiment may already be active.
                  </p>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => { setSimToast('idle'); simulateMutation.mutate(); }}
              disabled={simulateMutation.isPending || activeCount > 0}
              className="bg-white text-indigo-700 hover:bg-indigo-50 hover:text-indigo-800 border-none shrink-0"
            >
              {simulateMutation.isPending ? 'Injecting…' : <><ArrowRight size={15} /> Run End-to-End</>}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── MANUAL: Launch Experiment ──────────────────────────────── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Zap size={16} className="text-indigo-600" /> Launch Experiment
          </CardTitle>
          {selectedScenarioInfo && (
            <Badge variant={riskVariant(selectedScenarioInfo.risk) as any}>
              {selectedScenarioInfo.risk.toUpperCase()} RISK
            </Badge>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Failure Scenario</label>
              <Select value={selectedScenario} onChange={(e) => setSelectedScenario(e.target.value)}>
                {scenarios.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Target Service</label>
              <Select value={targetService} onChange={(e) => setTargetService(e.target.value)}>
                {services.map(svc => <option key={svc} value={svc}>{svc}</option>)}
              </Select>
            </div>
          </div>
          <Button
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending || activeCount > 0}
            className="w-full sm:w-auto"
          >
            <Play size={14} />
            {startMutation.isPending ? 'Launching...' : 'Launch Experiment'}
          </Button>
          {startMutation.isSuccess && (
            <div className="flex items-center gap-2 text-emerald-700 text-sm">
              <CheckCircle size={14} /> Experiment started successfully
            </div>
          )}
          {startMutation.isError && (
            <div className="flex items-center gap-2 text-red-700 text-sm">
              <AlertTriangle size={14} /> Failed to start. Another experiment may already be active.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active experiments */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-sm font-semibold">Active Experiments</CardTitle>
          {activeCount > 0 && <Badge variant="warning">{activeCount} running</Badge>}
        </CardHeader>
        <CardContent>
          {isLoading && <Skeleton className="h-12 w-full" />}
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
                      <p className="text-sm font-id font-semibold text-slate-900">{id}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                         Scenario: <span className="font-medium">{scenarios.find(s => String(s.id) === String(exp.scenario_id))?.name ?? exp.scenario_id}</span> · Target: <span className="font-medium">{exp.target_service}</span>
                       </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="warning" className="gap-1.5 animate-pulse">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600" /> Active
                      </Badge>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => stopMutation.mutate(id)}
                        disabled={stopMutation.isPending}
                        className="h-7 text-xs px-2"
                      >
                        <Square size={12} fill="currentColor" /> Stop
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
          {data?.error && <p className="text-sm text-red-600">{data.error}</p>}
        </CardContent>
      </Card>
    </div>
  );
};
