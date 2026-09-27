import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Server, Share2, AlertTriangle, Brain,
  RefreshCw, Zap, Activity, ClipboardList, Settings, Cpu,
  BrainCircuit
} from 'lucide-react';

const navGroups = [
  {
    title: 'Overview',
    items: [
      { name: 'Dashboard', path: '/', icon: LayoutDashboard },
      { name: 'Cluster View', path: '/cluster', icon: Server },
      { name: 'Live Topology', path: '/topology', icon: Share2 },
    ]
  },
  {
    title: 'Operations',
    items: [
      { name: 'Incident Center', path: '/incidents', icon: AlertTriangle },
      { name: 'AI Analysis', path: '/ai', icon: Brain },
      { name: 'Recovery Center', path: '/recovery', icon: RefreshCw },
    ]
  },
  {
    title: 'Reliability',
    items: [
      { name: 'Observability', path: '/observability', icon: Activity },
      { name: 'Chaos Engineering', path: '/chaos', icon: Zap },
    ]
  },
  {
    title: 'System',
    items: [
      { name: 'Audit Center', path: '/audit', icon: ClipboardList },
      { name: 'Memory Bank', path: '/memory', icon: BrainCircuit },
      { name: 'Settings', path: '/settings', icon: Settings },
    ]
  }
];

export const Sidebar = () => {
  const location = useLocation();
  return (
    <aside className="w-60 bg-white border-r border-[var(--color-border)] flex flex-col h-screen shrink-0"
      style={{ boxShadow: '2px 0 8px rgba(0,0,0,0.04)' }}>
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-[var(--color-border)]">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm">
          <Cpu size={16} className="text-white" />
        </div>
        <div>
          <span className="text-sm font-bold text-[var(--color-text-primary)] block leading-none">Hindsight</span>
          <span className="text-[10px] text-[var(--color-text-muted)] leading-none font-medium mt-1 block">Autonomous SRE</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-5">
        {navGroups.map((group) => (
          <div key={group.title} className="mt-2 first:mt-0">
            <h3 className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2 mt-4 first:mt-0">
              {group.title}
            </h3>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2.5 px-3 py-2 text-sm font-medium transition-all ${
                      active
                        ? 'bg-indigo-50 text-indigo-700 border-l-2 border-indigo-600 rounded-r-lg pl-2.5'
                        : 'text-slate-500 hover:bg-slate-50 rounded-lg'
                    }`}
                  >
                    <Icon size={15} className={active ? 'text-indigo-600' : 'text-slate-400'} />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[var(--color-border)] bg-slate-50/60">
        <div className="flex items-center gap-2 px-1">
          <div className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </div>
          <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wide">Live</span>
        </div>
      </div>
    </aside>
  );
};
