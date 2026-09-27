import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';

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
};

export const Layout = () => {
  const location = useLocation();
  const page = pageTitles[location.pathname] || { title: 'Hindsight Incident Agent', subtitle: '' };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top header bar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
          <div>
            <h1 className="text-base font-semibold text-slate-900 leading-none">{page.title}</h1>
            <p className="text-xs text-slate-400 mt-0.5">{page.subtitle}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-mono">{new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
            <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">SRE</span>
            </div>
          </div>
        </header>
        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
