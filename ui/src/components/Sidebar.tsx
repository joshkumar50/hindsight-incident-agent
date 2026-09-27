import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Server, Share2, AlertTriangle, Brain,
  RefreshCw, Zap, Activity, ClipboardList, Settings, Cpu
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
      { name: 'Settings', path: '/settings', icon: Settings },
    ]
  }
];

export const Sidebar = () => {
  const location = useLocation();
  return (
    <aside className="w-60 bg-white border-r border-slate-200 flex flex-col h-screen shrink-0">
      {/* Logo */}
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-200">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
          <Cpu size={16} className="text-white" />
        </div>
        <div>
          <span className="text-sm font-bold text-slate-900 block leading-none">Hindsight Incident Agent</span>
          <span className="text-xs text-slate-400 leading-none">Autonomous SRE</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-6">
        {navGroups.map((group) => (
          <div key={group.title}>
            <h3 className="px-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
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
                    className={`flex items-center gap-3 px-2 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      active
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
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
      <div className="p-4 border-t border-slate-200">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
          <span className="text-xs text-slate-500">All systems operational</span>
        </div>
      </div>
    </aside>
  );
};
