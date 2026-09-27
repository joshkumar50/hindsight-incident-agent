import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Compass, Zap, Terminal } from 'lucide-react';

interface ResultItem {
  id: string;
  type: 'page' | 'action';
  title: string;
  path?: string;
  icon?: React.ElementType;
}

const ITEMS: ResultItem[] = [
  // Pages
  { id: 'p1', type: 'page', title: 'Dashboard', path: '/', icon: Compass },
  { id: 'p2', type: 'page', title: 'Cluster View', path: '/cluster', icon: Compass },
  { id: 'p3', type: 'page', title: 'Live Topology', path: '/topology', icon: Compass },
  { id: 'p4', type: 'page', title: 'Incident Center', path: '/incidents', icon: Compass },
  { id: 'p5', type: 'page', title: 'AI Analysis', path: '/ai', icon: Compass },
  { id: 'p6', type: 'page', title: 'Recovery Center', path: '/recovery', icon: Compass },
  { id: 'p7', type: 'page', title: 'Chaos Engineering', path: '/chaos', icon: Compass },
  { id: 'p8', type: 'page', title: 'Observability', path: '/observability', icon: Compass },
  { id: 'p9', type: 'page', title: 'Audit Center', path: '/audit', icon: Compass },
  { id: 'p10', type: 'page', title: 'Memory Bank', path: '/memory', icon: Compass },
  { id: 'p11', type: 'page', title: 'Settings', path: '/settings', icon: Compass },
  
  // Quick Actions
  { id: 'a1', type: 'action', title: 'Run diagnostic', icon: Terminal },
  { id: 'a2', type: 'action', title: 'Seed memory', icon: Zap },
  { id: 'a3', type: 'action', title: 'Toggle chaos', icon: Zap },
];

export const CommandPalette = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const filtered = ITEMS.filter(item => item.title.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => (i + 1) % (filtered.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => (i - 1 + filtered.length) % (filtered.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = filtered[selectedIndex];
        if (item) {
          if (item.type === 'page' && item.path) {
            navigate(item.path);
          } else {
            console.log('Action triggered:', item.title); // Placeholder for action
          }
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, navigate, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-[560px] bg-white rounded-xl shadow-2xl overflow-hidden border border-slate-200 animate-[fadeIn_0.15s_ease-out]">
        <div className="flex items-center px-4 border-b border-slate-100">
          <Search size={18} className="text-slate-400" />
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent border-0 outline-none px-3 py-4 text-slate-700 text-sm placeholder:text-slate-400"
            placeholder="Search pages, incidents, services..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
          />
        </div>
        <div className="max-h-[300px] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-slate-500">No results found.</div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon || Compass;
              const showHeader = idx === 0 || item.type !== filtered[idx - 1].type;
              return (
                <React.Fragment key={item.id}>
                  {showHeader && (
                    <div className="px-4 py-2 mt-1 first:mt-0">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        {item.type === 'page' ? 'Pages' : 'Quick Actions'}
                      </h3>
                    </div>
                  )}
                  <div
                    className={`px-4 py-2 flex items-center gap-3 cursor-pointer ${
                      idx === selectedIndex ? 'bg-indigo-50' : 'hover:bg-slate-50'
                    }`}
                    onClick={() => {
                      if (item.type === 'page' && item.path) navigate(item.path);
                      else console.log('Action triggered:', item.title);
                      onClose();
                    }}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <div className={`p-1.5 rounded-lg ${idx === selectedIndex ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}>
                      <Icon size={14} />
                    </div>
                    <div className="flex flex-col">
                      <span className={`text-sm font-medium ${idx === selectedIndex ? 'text-indigo-900' : 'text-slate-700'}`}>
                        {item.title}
                      </span>
                    </div>
                  </div>
                </React.Fragment>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
