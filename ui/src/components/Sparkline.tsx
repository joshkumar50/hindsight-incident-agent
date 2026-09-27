import React from 'react';

interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  threshold?: number;
}

/**
 * Phase 2b — Pure SVG sparkline with gradient fill.
 * Pulses red when the latest value exceeds `threshold`, green otherwise.
 */
export const Sparkline: React.FC<SparklineProps> = ({
  data,
  color = '#6366f1',
  height = 36,
  threshold,
}) => {
  if (!data || data.length < 2) {
    return <div style={{ height, width: 100 }} className="bg-slate-100 rounded animate-pulse" />;
  }

  const width = 100;
  const padV = 3;
  const max = Math.max(...data, 1);
  const min = Math.min(...data);
  const range = max - min || 1;

  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = padV + ((max - v) / range) * (height - padV * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const polyline = pts.join(' ');
  const latest = data[data.length - 1];
  const isAlert = threshold !== undefined && latest > threshold;
  const strokeColor = isAlert ? '#ef4444' : color;
  const gradId = `grad-${Math.random().toString(36).slice(2, 7)}`;

  // Close path for gradient fill
  const fillPath =
    `M${pts[0]} ` +
    pts
      .slice(1)
      .map((p) => `L${p}`)
      .join(' ') +
    ` L${width},${height} L0,${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={isAlert ? 'animate-pulse' : undefined}
      aria-label="sparkline"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity={0.3} />
          <stop offset="100%" stopColor={strokeColor} stopOpacity={0.02} />
        </linearGradient>
      </defs>
      <path d={fillPath} fill={`url(#${gradId})`} />
      <polyline
        points={polyline}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
};
