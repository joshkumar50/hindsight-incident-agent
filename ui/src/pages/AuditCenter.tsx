import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { ClipboardList, CheckCircle, Download, FileJson, FileText, FileSearch } from 'lucide-react';

interface AuditLog {
  timestamp: string; event_type: string; incident_id?: string;
  decision?: string; confidence_score?: number; human_approved?: boolean;
}

const eventColor = (type: string) => {
  if (type.includes('REMEDIATION') || type.includes('RECOVERY')) return 'bg-emerald-50 text-emerald-700';
  if (type.includes('INCIDENT') || type.includes('ALERT')) return 'bg-red-50 text-red-700';
  if (type.includes('CHAOS')) return 'bg-amber-50 text-amber-700';
  return 'bg-indigo-50 text-indigo-700';
};

export const AuditCenter = () => {
  const [postmortemContent, setPostmortemContent] = useState<string | null>(null);
  const [postmortemLoading, setPostmortemLoading] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<AuditLog[]>({
    queryKey: ['audit'],
    queryFn: async () => { const res = await apiClient.get('/audit'); return res.data; }
  });

  // Export helpers — trigger file download via anchor
  const triggerDownload = (url: string, filename: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleExportCsv = () => {
    setExportStatus('Downloading CSV…');
    triggerDownload('/api/export/csv', 'audit_logs.csv');
    setTimeout(() => setExportStatus(null), 3000);
  };

  const handleExportJson = () => {
    setExportStatus('Downloading JSON…');
    triggerDownload('/api/export/json', 'audit_logs.json');
    setTimeout(() => setExportStatus(null), 3000);
  };

  // Phase 4a: Generate postmortem for first incident found
  const handlePostmortem = async () => {
    const incidentId = data?.find(l => l.incident_id)?.incident_id;
    if (!incidentId) {
      setPostmortemContent('No incident ID found in audit logs.');
      return;
    }
    setPostmortemLoading(true);
    setPostmortemContent(null);
    try {
      // BFF proxies to ai-copilot /postmortem
      const res = await apiClient.post('/ai/postmortem', { incident_id: incidentId });
      setPostmortemContent(res.data.markdown || 'No postmortem content returned.');
    } catch (e: any) {
      setPostmortemContent(`Postmortem generation failed: ${e.message}`);
    } finally {
      setPostmortemLoading(false);
    }
  };

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      {isLoading && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 animate-pulse h-48" />
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          Failed to connect to Audit Engine.
        </div>
      )}
      {data && data.length === 0 && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 flex items-center gap-4">
          <ClipboardList size={20} className="text-slate-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-slate-700">No audit events recorded</p>
            <p className="text-xs text-slate-500 mt-0.5">Events will appear here as the platform takes autonomous actions.</p>
          </div>
        </div>
      )}
      {data && data.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <ClipboardList size={15} className="text-indigo-600" />
              <h2 className="text-sm font-semibold text-slate-900">Decision Audit Trail</h2>
              <span className="text-xs text-slate-400">{data.length} events</span>
            </div>
            {/* Phase 4c: Export + Postmortem buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              {exportStatus && (
                <span className="text-xs text-emerald-600 font-medium">{exportStatus}</span>
              )}
              <button
                id="audit-export-csv-btn"
                onClick={handleExportCsv}
                className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
              >
                <FileText size={12} /> Export CSV
              </button>
              <button
                id="audit-export-json-btn"
                onClick={handleExportJson}
                className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
              >
                <FileJson size={12} /> Export JSON
              </button>
              <button
                id="audit-postmortem-btn"
                onClick={handlePostmortem}
                disabled={postmortemLoading}
                className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-60"
              >
                <FileSearch size={12} /> {postmortemLoading ? 'Generating…' : 'AI Postmortem'}
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50">
                  {['Timestamp', 'Event Type', 'Incident ID', 'Decision', 'Confidence', 'Approved'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((log, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-xs font-mono text-slate-500 whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '--'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${eventColor(log.event_type || '')}`}>
                        {log.event_type || '--'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-600">{log.incident_id || '--'}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">{log.decision || '--'}</td>
                    <td className="px-4 py-3 text-xs font-medium">
                      {log.confidence_score != null ? (
                        <span className={`px-1.5 py-0.5 rounded ${
                          log.confidence_score >= 0.9 ? 'text-emerald-700 bg-emerald-50' :
                          log.confidence_score >= 0.7 ? 'text-amber-700 bg-amber-50' :
                          'text-red-700 bg-red-50'
                        }`}>{(log.confidence_score * 100).toFixed(0)}%</span>
                      ) : '--'}
                    </td>
                    <td className="px-4 py-3">
                      {log.human_approved ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                          <CheckCircle size={11} /> Yes
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">Auto</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Phase 4a: Postmortem markdown output */}
      {postmortemContent && (
        <div className="bg-white border border-indigo-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <FileSearch size={15} className="text-indigo-600" />
            <h2 className="text-sm font-semibold text-slate-900">AI-Generated Postmortem</h2>
          </div>
          <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed bg-slate-50 rounded-lg p-4 overflow-auto max-h-96">
            {postmortemContent}
          </pre>
        </div>
      )}
    </div>
  );
};
