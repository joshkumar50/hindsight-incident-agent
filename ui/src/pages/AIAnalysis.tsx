import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Brain, CheckCircle, AlertTriangle } from 'lucide-react';

interface AIIncident {
  id: string; description: string;
  explanation?: { executive_summary?: string; technical_summary?: string; postmortem?: string; };
}

export const AIAnalysis = () => {
  const { data, isLoading, error } = useQuery<AIIncident[]>({
    queryKey: ['ai'],
    queryFn: async () => { const res = await apiClient.get('/ai'); return res.data; }
  });

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {isLoading && (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse h-32" />
          ))}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to AI Copilot.
        </div>
      )}
      {data && data.length === 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 flex items-center gap-4">
          <CheckCircle size={20} className="text-emerald-600 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-emerald-800">No incidents to analyze</p>
            <p className="text-xs text-emerald-600 mt-0.5">AI Copilot is idle. All systems are clear.</p>
          </div>
        </div>
      )}
      {data && data.length > 0 && (
        <div className="space-y-4">
          {data.map((item, idx) => (
            <div key={idx} className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md">
              <div className="flex items-center gap-3 px-5 py-4 bg-amber-50 border-b border-amber-100">
                <Brain size={16} className="text-amber-600" />
                <div>
                  <p className="text-sm font-semibold text-slate-900 font-mono">{item.id}</p>
                  <p className="text-xs text-slate-500">{item.description}</p>
                </div>
                <span className="ml-auto text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
                  <CheckCircle size={10} /> AI Analyzed
                </span>
              </div>
              <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Executive Summary</p>
                  <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {typeof item.explanation?.executive_summary === 'object' 
                      ? JSON.stringify(item.explanation.executive_summary, null, 2) 
                      : (item.explanation?.executive_summary || 'No summary available.')}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Technical Detail</p>
                  <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                    {typeof item.explanation?.technical_summary === 'object' 
                      ? JSON.stringify(item.explanation.technical_summary, null, 2) 
                      : (item.explanation?.technical_summary || 'No technical detail available.')}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Postmortem</p>
                  <p className="text-sm text-slate-600 leading-relaxed italic whitespace-pre-wrap">
                    {typeof item.explanation?.postmortem === 'object' 
                      ? JSON.stringify(item.explanation.postmortem, null, 2) 
                      : (item.explanation?.postmortem || 'No postmortem available.')}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
