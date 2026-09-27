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
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full ${
      isHealthy ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
      {status}
    </span>
  );
};

const KPICard = ({ label, value, sub, icon: Icon, color }: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color: string;
}) => (
  <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-3 hover:shadow-md hover:border-slate-300">
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</span>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
        <Icon size={14} />
      </div>
    </div>
    <div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  </div>
);

const HealthRow = ({ label, status }: { label: string; status: string }) => (
  <div className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
    <span className="text-sm text-slate-700 font-medium">{label}</span>
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
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse">
              <div className="h-3 bg-slate-100 rounded w-2/3 mb-4"></div>
              <div className="h-7 bg-slate-100 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle size={16} className="text-red-500 shrink-0" />
          <p className="text-sm text-red-700">Cannot connect to Dashboard BFF -- check if the service is running.</p>
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
              color="bg-emerald-50 text-emerald-600"
            />
            <KPICard
              label="Mean Time to Recover"
              value={`${data.mttr_seconds}s`}
              sub="Average across all incidents"
              icon={Clock}
              color="bg-indigo-50 text-indigo-600"
            />
            <KPICard
              label="Active Incidents"
              value={data.active_incidents}
              sub={data.active_incidents === 0 ? 'All clear' : 'Requires attention'}
              icon={AlertTriangle}
              color={data.active_incidents > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}
            />
            <KPICard
              label="Recovered"
              value={data.recovered_incidents}
              sub="Autonomous resolutions"
              icon={RefreshCw}
              color="bg-violet-50 text-violet-600"
            />
          </div>

          {/* Autonomous Pilot Real-time Stepper Timeline */}
          <AutonomousPilotTimeline />

          {/* Two column layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Health Status */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Shield size={16} className="text-indigo-600" />
                <h2 className="text-sm font-semibold text-slate-900">Health Status</h2>
              </div>
              <HealthRow label="Cluster Health" status={data.cluster_health} />
              <HealthRow label="Application Health" status={data.app_health} />
              <HealthRow label="Platform Health" status={data.platform_health} />
            </div>

            {/* System Pulse */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Activity size={16} className="text-indigo-600" />
                <h2 className="text-sm font-semibold text-slate-900">Autonomous SRE Activity</h2>
              </div>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-slate-600">Decision Engine active -- enforcing policy</p>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-slate-600">Anomaly Detector: rolling Z-score scanning</p>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-slate-600">Recovery Validator: closed-loop verification on</p>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-slate-600">AI Copilot: Online -- generating incident summaries</p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
