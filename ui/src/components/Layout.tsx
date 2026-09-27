import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

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
        <main className="flex-1 overflow-y-auto p-8">
          <div key={location.pathname} className="animate-[fadeIn_0.15s_ease-out]">
            <Outlet />
          </div>
        </main>
      </div>
      <CommandPalette isOpen={isCommandOpen} onClose={() => setIsCommandOpen(false)} />
    </div>
  );
};
