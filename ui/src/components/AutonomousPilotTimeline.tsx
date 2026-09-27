import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, AlertOctagon, ArrowRight, ShieldAlert, Cpu } from 'lucide-react';

export interface PilotEvent {
  incident_id: string;
  target: string;
  phase: 'DIAGNOSING' | 'APPLYING_FIX' | 'VERIFYING_HEALTH' | 'STABILIZED' | 'ROLLBACK_REQUIRED' | 'ROLLBACK_EXECUTED' | 'APPROVAL_GRANTED';
  ts: string | number;
}

const PHASES = [
  { key: 'DIAGNOSING', label: 'Diagnosing' },
  { key: 'APPLYING_FIX', label: 'Applying Fix' },
  { key: 'VERIFYING_HEALTH', label: 'Verifying Health' },
  { key: 'STABILIZED', label: 'Stabilized' }
];

export const AutonomousPilotTimeline: React.FC = () => {
  const [events, setEvents] = useState<PilotEvent[]>([]);
  const [connected, setConnected] = useState<boolean>(false);

  useEffect(() => {
    let es: EventSource | null = null;
    try {
      es = new EventSource('/api/stream/pilot');
      es.onopen = () => setConnected(true);
      es.onerror = () => setConnected(false);

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data && data.incident_id) {
            setEvents((prev) => [data, ...prev.filter(x => !(x.incident_id === data.incident_id && x.phase === data.phase))].slice(0, 20));
          }
        } catch {
          // ignore parse errors
        }
      };
    } catch {
      setConnected(false);
    }

    return () => {
      if (es) es.close();
    };
  }, []);

  // Group latest event per incident_id
  const incidentMap = new Map<string, PilotEvent>();
  events.forEach((ev) => {
    if (!incidentMap.has(ev.incident_id)) {
      incidentMap.set(ev.incident_id, ev);
    }
  });
  const recentIncidents = Array.from(incidentMap.values()).slice(0, 5);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-indigo-600 animate-pulse" />
          <h2 className="text-sm font-semibold text-slate-900">Autonomous Self-Healing Pilot</h2>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-amber-400'}`}></span>
          <span>{connected ? 'Live Stream' : 'Awaiting Events'}</span>
        </div>
      </div>

      {recentIncidents.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs">
          <Cpu className="mx-auto mb-2 text-slate-300" size={24} />
          No active remediation workflows. Fleet is stabilized.
        </div>
      ) : (
        <div className="space-y-4">
          {recentIncidents.map((inc) => {
            const isRollback = inc.phase === 'ROLLBACK_REQUIRED' || inc.phase === 'ROLLBACK_EXECUTED';
            const isStabilized = inc.phase === 'STABILIZED';

            return (
              <div key={inc.incident_id} className="p-3 bg-slate-50 border border-slate-100 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-800">
                    Incident: <code className="text-indigo-600 font-mono text-[11px]">{inc.incident_id}</code>
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-slate-200 text-slate-700">
                    Target: {inc.target}
                  </span>
                </div>

                {/* Horizontal / Vertical Stepper */}
                <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                  {PHASES.map((p, idx) => {
                    let stateColor = 'bg-slate-200 text-slate-500';
                    let isCurrent = inc.phase === p.key;

                    if (isRollback) {
                      stateColor = 'bg-rose-100 text-rose-700 border border-rose-200';
                    } else if (isStabilized) {
                      stateColor = 'bg-emerald-100 text-emerald-800 font-semibold';
                    } else if (isCurrent) {
                      stateColor = 'bg-amber-100 text-amber-800 border border-amber-300 animate-pulse font-semibold';
                    }

                    return (
                      <div key={p.key} className={`p-2 rounded-md text-xs flex flex-col items-center justify-center ${stateColor}`}>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Step {idx + 1}</span>
                        <span>{p.label}</span>
                      </div>
                    );
                  })}
                </div>

                {isRollback && (
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-rose-600 bg-rose-50 p-1.5 rounded">
                    <AlertOctagon size={13} />
                    <span>Verification failed. Rollback executed autonomously to protect SLA.</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
