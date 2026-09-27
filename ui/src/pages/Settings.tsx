import React from 'react';
import { useStore } from '../store/useStore';
import { Settings as SettingsIcon, Cpu, Database, Radio, Info, ToggleLeft, ToggleRight } from 'lucide-react';

const StatusPill = ({ status, color }: { status: string; color: 'green' | 'amber' | 'red' }) => {
  const map = {
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    red: 'bg-red-50 text-red-700 border-red-200',
  };
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${map[color]}`}>{status}</span>
  );
};

const SettingRow = ({ icon: Icon, title, desc, children }: {
  icon: React.ElementType; title: string; desc: string; children: React.ReactNode;
}) => (
  <div className="flex items-center justify-between py-4 border-b border-slate-100 last:border-0">
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 bg-slate-50 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
        <Icon size={14} className="text-slate-500" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-900">{title}</p>
        <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
      </div>
    </div>
    <div className="shrink-0 ml-4">{children}</div>
  </div>
);

export const Settings = () => {
  const { isPollingActive, setPollingActive } = useStore();

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Platform info */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 flex items-start gap-3">
        <Info size={14} className="text-indigo-600 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-indigo-900">Hindsight Incident Agent v1.0.0</p>
          <p className="text-xs text-indigo-600 mt-0.5">Autonomous Kubernetes SRE Platform -- Hackathon Build</p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
        <div className="px-5 py-4 bg-slate-50">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Configuration</h2>
        </div>
        <div className="px-5">
          <SettingRow
            icon={Radio}
            title="Live Data Polling"
            desc="Enable real-time data refresh across all pages (every 3s)"
          >
            <button
              onClick={() => setPollingActive(!isPollingActive)}
              className="flex items-center gap-2"
              aria-label="Toggle live polling"
            >
              {isPollingActive ? (
                <ToggleRight size={28} className="text-indigo-600" />
              ) : (
                <ToggleLeft size={28} className="text-slate-300" />
              )}
              <span className={`text-xs font-medium ${isPollingActive ? 'text-indigo-600' : 'text-slate-400'}`}>
                {isPollingActive ? 'On' : 'Off'}
              </span>
            </button>
          </SettingRow>
          <SettingRow
            icon={Cpu}
            title="AI Engine"
            desc="Autonomous ReAct Agent (Gemini 1.5 / Bedrock / Ollama)"
          >
            <StatusPill status="Connected" color="green" />
          </SettingRow>
          <SettingRow
            icon={Database}
            title="Persistent Memory"
            desc="Vectorize Hindsight Cloud Semantic Storage"
          >
            <StatusPill status="Connected" color="green" />
          </SettingRow>
          <SettingRow
            icon={SettingsIcon}
            title="Telemetry"
            desc="OpenTelemetry collector -> Prometheus -> Grafana"
          >
            <StatusPill status="Active" color="green" />
          </SettingRow>
        </div>
      </div>
    </div>
  );
};
