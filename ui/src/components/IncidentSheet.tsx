import { useEffect } from 'react';
import { X, AlertTriangle, Clock, Zap, CheckCircle2 } from 'lucide-react';

interface Incident { id: string; description: string; status: string; 
                     severity: string; root_cause?: string; 
                     impacted_services?: string[]; timestamp?: number; }

export const IncidentSheet = ({ incident, open, onClose }: {
  incident: Incident | null; open: boolean; onClose: () => void;
}) => {
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [onClose]);

  return (
    <div className={`fixed inset-0 z-50 transition-opacity duration-200 ${open ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-[2px]" onClick={onClose} />
      <div className={`absolute right-0 top-0 h-full w-[480px] bg-white shadow-2xl 
                       transition-transform duration-300 ease-out
                       ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        {incident && (
          <>
            <header className="h-14 border-b border-slate-200 px-5 flex items-center gap-3">
              <AlertTriangle size={16} className="text-rose-500" />
              <span className="font-mono text-xs text-slate-500">{incident.id}</span>
              <span className="flex-1" />
              <button onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors">
                <X size={16} />
              </button>
            </header>
            <div className="p-5 overflow-y-auto h-[calc(100%-56px)] space-y-5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700">
                  {incident.severity.toUpperCase()}
                </span>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {incident.status}
                </span>
              </div>

              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Description</p>
                <p className="text-sm text-slate-800 leading-relaxed">{incident.description}</p>
              </div>

              {incident.root_cause && (
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Root Cause</p>
                  <p className="text-sm text-slate-800 font-mono bg-slate-50 rounded-md px-3 py-2">
                    {incident.root_cause}
                  </p>
                </div>
              )}

              {incident.impacted_services && incident.impacted_services.length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Impacted Services
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {incident.impacted_services.map((s, i) => (
                      <span key={i} className="text-xs font-mono bg-orange-50 text-orange-700 
                                               border border-orange-200 rounded px-2 py-0.5">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {incident.timestamp && (
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Clock size={11} />
                  <span>Started {new Date(incident.timestamp * 1000).toLocaleString()}</span>
                </div>
              )}

              <div className="pt-3 border-t border-slate-100">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Timeline
                </p>
                <div className="space-y-3">
                  {[
                    { icon: AlertTriangle, label: 'Detected', color: 'text-rose-500', time: '0s' },
                    { icon: Zap, label: 'Diagnosed', color: 'text-indigo-500', time: '1.5s' },
                    { icon: CheckCircle2, label: 'Resolved', color: 'text-emerald-500', time: '8.3s' },
                  ].map((step, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className={`w-6 h-6 rounded-full bg-slate-50 flex items-center justify-center ${step.color}`}>
                        <step.icon size={12} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-800">{step.label}</p>
                        <p className="text-xs text-slate-400 font-mono">+{step.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
