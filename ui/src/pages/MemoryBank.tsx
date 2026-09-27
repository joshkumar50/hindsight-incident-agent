import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import { BrainCircuit, Search, Database, ArrowRight, CheckCircle2, UserCheck, UserCog, UserX, AlertCircle, Play } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Memory {
  incident_id: string;
  symptoms: string;
  root_cause: string;
  playbook: string[];
  success_rate: number;
  outcome: string;
  human_approved: boolean;
}

interface MemoryBankResponse {
  bank_id: string;
  total_memories: number;
  memories: Memory[];
}

export const MemoryBank = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery<MemoryBankResponse>({
    queryKey: ['memory-bank'],
    queryFn: () => apiGet<MemoryBankResponse>('/memory/bank'),
    refetchInterval: 5000,
  });

  const seedMutation = useMutation({
    mutationFn: () => apiPost('/memory/seed-demo'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory-bank'] });
    },
  });

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case 'success':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 border border-green-200"><CheckCircle2 size={12} /> Success</span>;
      case 'human_validated':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"><UserCheck size={12} /> Human Validated</span>;
      case 'human_modified':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"><UserCog size={12} /> Human Modified</span>;
      case 'human_rejected':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-red-50 text-red-700 border border-red-200"><UserX size={12} /> Human Rejected</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-slate-50 text-slate-700 border border-slate-200"><AlertCircle size={12} /> {outcome}</span>;
    }
  };

  const memories = data?.memories || [];
  const filteredMemories = memories.filter(m => 
    m.symptoms.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.root_cause.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.incident_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <BrainCircuit className="text-indigo-600" />
            Hindsight Memory Bank
          </h1>
          <p className="text-[var(--color-text-secondary)] mt-1">
            Persistent incident knowledge and runbook evolution.
          </p>
        </div>
        <button 
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending}
          className="btn-primary flex items-center gap-2"
        >
          {seedMutation.isPending ? 'Seeding...' : 'Retain a demo memory'}
          <Database size={16} />
        </button>
      </div>

      {/* Header Card */}
      <div className="premium-card p-6 flex flex-wrap gap-8 items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <Database className="text-indigo-600" size={24} />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--color-text-secondary)]">Active Bank</p>
            <p className="text-lg font-bold text-[var(--color-text-primary)]">{data?.bank_id || 'hindsight-incident-agent'}</p>
          </div>
        </div>
        <div className="flex items-center gap-8">
          <div className="text-right">
            <p className="text-sm font-medium text-[var(--color-text-secondary)]">Total Memories</p>
            <p className="text-2xl font-bold text-indigo-600">{data?.total_memories || 0}</p>
          </div>
          <div className="h-10 w-px bg-[var(--color-border)]"></div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="text-sm font-medium text-[var(--color-text-primary)]">Connected to Hindsight Cloud</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="premium-card overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border)] bg-slate-50 flex items-center gap-3">
          <Search className="text-[var(--color-text-muted)]" size={18} />
          <input 
            type="text" 
            placeholder="Search symptoms, root causes, or incident IDs..." 
            className="bg-transparent border-none focus:ring-0 text-sm flex-1 text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] outline-none"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-[var(--color-text-muted)] flex flex-col items-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
            Loading memory bank...
          </div>
        ) : isError ? (
          <div className="p-12 text-center text-red-500 flex flex-col items-center">
            <AlertCircle size={32} className="mb-2" />
            <p>Failed to load memory bank.</p>
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="p-16 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center mb-4">
              <BrainCircuit className="text-indigo-400" size={32} />
            </div>
            <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-2">Memory Bank is Empty</h3>
            <p className="text-[var(--color-text-secondary)] mb-6 max-w-md">
              No memories retained yet. Run the first diagnostic to seed memory and build the knowledge base.
            </p>
            <Link to="/incidents" className="btn-primary flex items-center gap-2">
              Go to Incident Center <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {filteredMemories.map((memory, i) => (
              <div key={i} className="p-6 hover:bg-slate-50/50 transition-colors">
                <div className="flex flex-col lg:flex-row gap-6">
                  {/* Left Column */}
                  <div className="flex-1 space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="font-mono text-xs font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded">
                          {memory.incident_id}
                        </span>
                        <h3 className="text-base font-bold text-[var(--color-text-primary)] mt-2 line-clamp-2">
                          {memory.symptoms}
                        </h3>
                      </div>
                      <div className="flex-shrink-0 ml-4">
                        {getOutcomeBadge(memory.outcome)}
                      </div>
                    </div>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      <span className="font-medium text-[var(--color-text-primary)]">Root Cause:</span> {memory.root_cause}
                    </p>
                  </div>
                  
                  {/* Right Column */}
                  <div className="flex-1 space-y-4 lg:border-l lg:border-[var(--color-border)] lg:pl-6">
                    <div>
                      <h4 className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Play size={12} /> Playbook
                      </h4>
                      <ol className="list-decimal list-inside space-y-1 text-sm text-[var(--color-text-secondary)]">
                        {memory.playbook.map((step, idx) => (
                          <li key={idx} className="line-clamp-1" title={step}>{step}</li>
                        ))}
                      </ol>
                    </div>
                    
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-[var(--color-text-secondary)]">Success Rate</span>
                        <span className="text-xs font-bold text-emerald-600">{Math.round(memory.success_rate * 100)}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5">
                        <div 
                          className="bg-emerald-500 h-1.5 rounded-full" 
                          style={{ width: `${Math.round(memory.success_rate * 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
