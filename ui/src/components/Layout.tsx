import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Play, RotateCcw, BrainCircuit } from 'lucide-react';
import { useStore } from '../store/useStore';

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  '/': { title: 'Executive Dashboard', subtitle: 'Real-time platform health and SRE metrics' },
  '/cluster': { title: 'Cluster View', subtitle: 'Kubernetes nodes, pods, and services' },
  '/topology': { title: 'Live Topology', subtitle: 'Interactive service dependency graph' },
  '/incidents': { title: 'Incident Center', subtitle: 'Active and resolved incidents' },
  '/ai': { title: 'AI Analysis', subtitle: 'Copilot-powered incident explanations' },
  '/recovery': { title: 'Recovery Center', subtitle: 'Autonomous remediation metrics' },
  '/chaos': { title: 'Chaos Engineering', subtitle: 'Controlled failure injection experiments' },
  '/observability': { title: 'Observability', subtitle: 'Traces, metrics, and service health' },
  '/audit': { title: 'Audit Center', subtitle: 'Decision audit trail and compliance log' },
  '/settings': { title: 'Settings', subtitle: 'Platform configuration and integrations' },
  '/memory': { title: 'Memory Bank', subtitle: 'Hindsight knowledge persistence' },
};

export const Layout = () => {
  const location = useLocation();
  const page = pageTitles[location.pathname] || { title: 'Hindsight Incident Agent', subtitle: '' };

  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [timeAgoStr, setTimeAgoStr] = useState<string>('just now');
  const [isConnected, setIsConnected] = useState<boolean>(true);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const navigate = useNavigate();
  const { lastDiagnostic, setLastDiagnostic } = useStore();
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoScenario, setDemoScenario] = useState('checkout_500');
  const [toastMsg, setToastMsg] = useState('');

  const handleReset = async () => {
    setDemoLoading(true);
    try {
      await apiClient.post('/demo/reset');
      setToastMsg('Memory bank reset · 5 incidents seeded');
      setTimeout(() => setToastMsg(''), 3000);
    } catch (e) {
      console.error(e);
    }
    setDemoLoading(false);
  };

  const handleRunDemo = async () => {
    setDemoLoading(true);
    try {
      const res = await apiClient.post('/demo/trigger', { scenario: demoScenario });
      const data = res.data;
      if (data && data.root_cause_analysis) {
        setLastDiagnostic({
          query: data.query,
          mode: data.root_cause_analysis.llm_model_used === 'hindsight-semantic-memory' ? 'recall' : 'fresh',
          durationSeconds: data.root_cause_analysis.analysis_duration_seconds,
          confidence: data.root_cause_analysis.confidence_score,
          incidentId: data.root_cause_analysis.incident_id,
          timestamp: new Date().toISOString()
        });
      }
      navigate('/incidents');
    } catch (e) {
      console.error(e);
    }
    setDemoLoading(false);
  };

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsCommandOpen(open => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  useEffect(() => {
    const ping = async () => {
      try {
        await apiClient.get('/dashboard');
        setLastUpdate(new Date());
        setIsConnected(true);
      } catch (err) {
        setIsConnected(false);
      }
    };
    ping();
    const interval = setInterval(ping, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      const sec = Math.floor((new Date().getTime() - lastUpdate.getTime()) / 1000);
      if (sec < 2) setTimeAgoStr('just now');
      else if (sec < 60) setTimeAgoStr(`${sec}s ago`);
      else setTimeAgoStr(`${Math.floor(sec / 60)}m ago`);
    }, 1000);
    return () => clearInterval(interval);
  }, [lastUpdate]);

  return (
    <div className="flex h-screen bg-[var(--color-bg-primary)] overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top header bar */}
        <header className="h-16 bg-white border-b border-[var(--color-border)] flex items-center justify-between px-8 shrink-0"
          style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
          <div>
            <h1 className="text-base font-semibold text-[var(--color-text-primary)] leading-none">{page.title}</h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{page.subtitle}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-[var(--color-border)]">
              <span className="relative flex h-1.5 w-1.5 mr-1">
                {isConnected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${isConnected ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
              </span>
              <span className="text-[11px] text-slate-500 font-medium">Live</span>
              <span className="text-slate-300">·</span>
              <span className="text-[11px] text-slate-400 font-mono">updated {timeAgoStr}</span>
            </div>
            <span className="text-[11px] text-[var(--color-text-muted)] font-mono">
              {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </span>
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shadow-sm">
              <span className="text-white text-xs font-bold">SRE</span>
            </div>
          </div>
        </header>
        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          
          {/* Demo Mode Bar */}
          <div className="absolute top-4 right-8 z-20 flex items-center gap-3 bg-slate-100 rounded-lg p-1.5 border border-slate-200 shadow-sm text-xs">
            {lastDiagnostic && (
              <div className="flex items-center gap-1.5 px-3 border-r border-slate-200">
                <BrainCircuit size={12} className={lastDiagnostic.mode === 'recall' ? 'text-indigo-600' : 'text-slate-500'} />
                <span className="font-medium text-slate-600">
                  Last: {lastDiagnostic.mode === 'recall' ? 'RECALL HIT' : 'FRESH'} · {lastDiagnostic.durationSeconds.toFixed(1)}s
                </span>
              </div>
            )}
            
            <select 
              className="bg-white border border-slate-200 rounded px-2 py-1 text-slate-700 outline-none hover:border-indigo-300 transition-colors"
              value={demoScenario}
              onChange={e => setDemoScenario(e.target.value)}
              disabled={demoLoading}
            >
              <option value="checkout_500">Checkout 500s</option>
              <option value="auth_oom">Auth OOM</option>
              <option value="payment_timeout">Payment Timeout</option>
            </select>
            
            <button 
              onClick={handleRunDemo}
              disabled={demoLoading}
              className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-indigo-50 hover:text-indigo-600 rounded text-slate-700 font-medium transition-colors disabled:opacity-50 border border-slate-200"
            >
              <Play size={12} /> {demoLoading ? 'Running...' : 'Run demo'}
            </button>
            
            <button 
              onClick={handleReset}
              disabled={demoLoading}
              className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-indigo-50 hover:text-indigo-600 rounded text-slate-700 font-medium transition-colors disabled:opacity-50 border border-slate-200"
            >
              <RotateCcw size={12} /> Reset
            </button>
          </div>

          {toastMsg && (
            <div className="absolute top-16 right-8 z-30 bg-emerald-600 text-white text-xs font-medium px-4 py-2 rounded shadow-lg animate-[fadeIn_0.15s_ease-out]">
              {toastMsg}
            </div>
          )}

          <div key={location.pathname} className="animate-[fadeIn_0.15s_ease-out] mt-6">
            <Outlet />
          </div>
        </main>
      </div>
      <CommandPalette isOpen={isCommandOpen} onClose={() => setIsCommandOpen(false)} />
    </div>
  );
};
