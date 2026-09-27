import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { CheckCircle, AlertTriangle, Clock, Activity, Shield, TrendingUp, Zap, RefreshCw } from 'lucide-react';
import { AutonomousPilotTimeline } from '../components/AutonomousPilotTimeline';

interface DashboardData {
  cluster_health: string;
  app_health: string;
  platform_health: string;
  mttr_seconds: number;
  active_incidents: number;
  recovered_incidents: number;
  system_availability: number;
}

const StatusBadge = ({ status }: { status: string }) => {
  const isHealthy = status === 'Healthy';
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${
      isHealthy
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : 'bg-amber-50 text-amber-700 border-amber-200'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></span>
      {status}
    </span>
  );
};

const KPICard = ({ label, value, sub, icon: Icon, color, bgColor }: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color: string; bgColor: string;
}) => (
  <div className="premium-card p-5 flex flex-col gap-3">
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">{label}</span>
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${bgColor}`}>
        <Icon size={16} className={color} />
      </div>
    </div>
    <div>
      <p className="text-3xl font-bold text-[var(--color-text-primary)] tracking-tight">{value}</p>
      {sub && <p className="text-xs text-[var(--color-text-muted)] mt-1">{sub}</p>}
    </div>
  </div>
);

const HealthRow = ({ label, status }: { label: string; status: string }) => (
  <div className="flex items-center justify-between py-3 border-b border-[var(--color-border)] last:border-0">
    <span className="text-sm text-[var(--color-text-secondary)] font-medium">{label}</span>
    <StatusBadge status={status} />
  </div>
);

export const ExecutiveDashboard = () => {
  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/dashboard');
      return res.data;
    }
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="premium-card p-5 animate-pulse">
              <div className="h-3 bg-slate-100 rounded w-2/3 mb-4"></div>
              <div className="h-8 bg-slate-100 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="premium-card border-red-200 bg-red-50 p-4 flex items-center gap-3">
          <AlertTriangle size={16} className="text-red-500 shrink-0" />
          <p className="text-sm text-red-700">Cannot connect to Dashboard BFF — check if the service is running.</p>
        </div>
      )}

      {data && (
        <>
          {/* KPI Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard
              label="System Availability"
              value={`${data.system_availability}%`}
              sub="Last 30 days"
              icon={TrendingUp}
              color="text-emerald-600"
              bgColor="bg-emerald-50"
            />
            <KPICard
              label="Mean Time to Recover"
              value={`${data.mttr_seconds}s`}
              sub="Average across all incidents"
              icon={Clock}
              color="text-indigo-600"
              bgColor="bg-indigo-50"
            />
            <KPICard
              label="Active Incidents"
              value={data.active_incidents}
              sub={data.active_incidents === 0 ? 'All clear' : 'Requires attention'}
              icon={AlertTriangle}
              color={data.active_incidents > 0 ? 'text-red-600' : 'text-emerald-600'}
              bgColor={data.active_incidents > 0 ? 'bg-red-50' : 'bg-emerald-50'}
            />
            <KPICard
              label="Recovered"
              value={data.recovered_incidents}
              sub="Autonomous resolutions"
              icon={RefreshCw}
              color="text-violet-600"
              bgColor="bg-violet-50"
            />
          </div>

          {/* Last Diagnostic Badge */}
          <div className="premium-card p-4 flex items-center justify-between" style={{ background: 'rgba(168, 85, 247, 0.05)', borderLeft: '4px solid var(--accent-purple)' }}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full flex items-center justify-center bg-purple-100 text-purple-600 shadow-[0_0_15px_rgba(168,85,247,0.4)] animate-pulse">
                🧠
              </div>
              <div>
                <h3 className="text-sm font-bold text-purple-700 tracking-tight uppercase">HINDSIGHT RECALL HIT</h3>
                <p className="text-xs text-[var(--color-text-secondary)] font-medium">Last Diagnostic: 0.1s &middot; 0 LLM tokens &middot; playbook from memory</p>
              </div>
            </div>
            <button className="text-xs font-semibold px-3 py-1.5 rounded-md bg-white border border-purple-200 text-purple-700 hover:bg-purple-50 transition-colors">
              View Case
            </button>
          </div>

          {/* Autonomous Pilot Real-time Stepper Timeline */}
          <AutonomousPilotTimeline />

          {/* Two column layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Health Status */}
            <div className="premium-card p-5">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
                  <Shield size={15} className="text-indigo-600" />
                </div>
                <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Health Status</h2>
              </div>
              <HealthRow label="Cluster Health" status={data.cluster_health} />
              <HealthRow label="Application Health" status={data.app_health} />
              <HealthRow label="Platform Health" status={data.platform_health} />
            </div>

            {/* System Pulse */}
            <div className="premium-card p-5">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
                  <Activity size={15} className="text-indigo-600" />
                </div>
                <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Autonomous SRE Activity</h2>
              </div>
              <div className="space-y-3">
                {[
                  'Decision Engine active — enforcing policy',
                  'Anomaly Detector: rolling Z-score scanning',
                  'Recovery Validator: closed-loop verification on',
                  'AI Copilot: Online — generating incident summaries',
                ].map((msg, i) => (
                  <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-50/80 border border-[var(--color-border)]">
                    <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                    <p className="text-sm text-[var(--color-text-secondary)]">{msg}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
