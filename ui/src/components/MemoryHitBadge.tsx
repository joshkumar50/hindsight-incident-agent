import React, { useEffect, useRef } from 'react';
import { BrainCircuit, Search } from 'lucide-react';

export interface MemoryHitBadgeProps {
  mode: 'recall' | 'fresh';
  durationSeconds: number;
  confidence: number;
  incidentId?: string;
}

const MemoryHitBadge: React.FC<MemoryHitBadgeProps> = ({
  mode,
  durationSeconds,
  confidence,
  incidentId,
}) => {
  const isRecall = mode === 'recall';

  // Purple for recall, amber for fresh
  const palette = isRecall
    ? {
        bg: '#faf5ff',
        border: '#e9d5ff',
        text: '#6b21a8',
        subtext: '#7c3aed',
        chipBg: '#f3e8ff',
        chipBorder: '#d8b4fe',
        chipText: '#6b21a8',
        dotColor: '#a855f7',
      }
    : {
        bg: '#fffbeb',
        border: '#fde68a',
        text: '#92400e',
        subtext: '#b45309',
        chipBg: '#fef3c7',
        chipBorder: '#fcd34d',
        chipText: '#92400e',
        dotColor: '#f59e0b',
      };

  const confidencePct = Math.round(confidence * 100);
  const subtitle = isRecall
    ? `${durationSeconds.toFixed(1)}s · 0 LLM tokens · playbook from memory`
    : `${durationSeconds.toFixed(1)}s · ReAct loop · playbook retained to memory`;

  const dotRef = useRef<HTMLSpanElement>(null);

  // Pulse animation on mount via class toggle
  useEffect(() => {
    const el = dotRef.current;
    if (!el) return;
    el.classList.add('animate-ping');
    const t = setTimeout(() => el.classList.remove('animate-ping'), 1200);
    return () => clearTimeout(t);
  }, [mode]);

  return (
    <div
      role="status"
      aria-label={isRecall ? 'Hindsight Recall Hit' : 'Fresh Reasoning'}
      style={{
        background: palette.bg,
        border: `1px solid ${palette.border}`,
        borderLeft: `4px solid ${palette.dotColor}`,
      }}
      className="w-full rounded-xl px-5 py-4 flex items-center justify-between gap-4 shadow-sm"
    >
      {/* Left: icon + title + subtitle */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Icon with pulsing dot overlay */}
        <div className="relative shrink-0">
          <div
            style={{ background: isRecall ? '#f3e8ff' : '#fef3c7' }}
            className="w-10 h-10 rounded-xl flex items-center justify-center"
          >
            {isRecall
              ? <BrainCircuit size={20} style={{ color: palette.dotColor }} />
              : <Search size={20} style={{ color: palette.dotColor }} />
            }
          </div>
          {/* Live pulse dot */}
          <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
            <span
              ref={dotRef}
              style={{ background: palette.dotColor }}
              className="inline-flex rounded-full h-3 w-3 opacity-75"
            />
            <span
              style={{ background: palette.dotColor }}
              className="relative inline-flex rounded-full h-3 w-3 -ml-3"
            />
          </span>
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p
              className="text-xs font-extrabold uppercase tracking-widest"
              style={{ color: palette.text }}
            >
              {isRecall ? 'HINDSIGHT RECALL HIT' : 'FRESH REASONING'}
            </p>
            {incidentId && (
              <span
                style={{
                  background: palette.chipBg,
                  border: `1px solid ${palette.chipBorder}`,
                  color: palette.chipText,
                }}
                className="text-xs font-mono font-semibold px-2 py-0.5 rounded-md"
              >
                {incidentId}
              </span>
            )}
          </div>
          <p className="text-xs mt-0.5 truncate" style={{ color: palette.subtext }}>
            {subtitle}
          </p>
        </div>
      </div>

      {/* Right: confidence chip */}
      <div
        style={{
          background: palette.chipBg,
          border: `1px solid ${palette.chipBorder}`,
          color: palette.chipText,
        }}
        className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-full"
      >
        {confidencePct}% confidence
      </div>
    </div>
  );
};

export default MemoryHitBadge;
