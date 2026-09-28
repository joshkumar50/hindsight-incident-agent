import React from 'react';
import { useStore } from '../store/useStore';
import { Settings as SettingsIcon, Cpu, Database, Radio, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';

const SettingRow = ({ icon: Icon, title, desc, children }: {
  icon: React.ElementType; title: string; desc: string; children: React.ReactNode;
}) => (
  <div className="flex items-center justify-between py-4">
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
    <div className="space-y-4 max-w-2xl mx-auto">
      {/* Platform info */}
      <Card className="bg-indigo-50 border-indigo-100">
        <CardContent className="p-4 flex items-start gap-3">
          <Info size={14} className="text-indigo-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-indigo-900">Hindsight Incident Agent v1.0.0</p>
            <p className="text-xs text-indigo-600 mt-0.5">Autonomous Kubernetes SRE Platform -- Enterprise Build</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="bg-slate-50 border-b border-slate-100 py-3">
          <CardTitle className="text-xs uppercase tracking-wide text-slate-500">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="p-0 px-5">
          <SettingRow
            icon={Radio}
            title="Live Data Polling"
            desc="Enable real-time data refresh across all pages (every 3s)"
          >
            <div className="flex items-center gap-3">
              <span className={`text-xs font-medium ${isPollingActive ? 'text-indigo-600' : 'text-slate-400'}`}>
                {isPollingActive ? 'On' : 'Off'}
              </span>
              <Switch
                checked={isPollingActive}
                onChange={(e) => setPollingActive(e.target.checked)}
                data-state={isPollingActive ? 'checked' : 'unchecked'}
              />
            </div>
          </SettingRow>
          <Separator />
          <SettingRow
            icon={Cpu}
            title="AI Engine"
            desc="Local Ollama LLM -- strictly for natural language explanations only"
          >
            <Badge variant="warning">Offline</Badge>
          </SettingRow>
          <Separator />
          <SettingRow
            icon={Database}
            title="Event Bus"
            desc="Redis Streams in incident-agent-system namespace"
          >
            <Badge variant="success">Connected</Badge>
          </SettingRow>
          <Separator />
          <SettingRow
            icon={SettingsIcon}
            title="Telemetry"
            desc="OpenTelemetry collector -> Prometheus -> Grafana"
          >
            <Badge variant="success">Active</Badge>
          </SettingRow>
        </CardContent>
      </Card>
    </div>
  );
};
