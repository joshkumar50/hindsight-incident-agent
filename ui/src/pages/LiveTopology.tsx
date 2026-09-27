import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import {
  ReactFlow, Background, Controls, MiniMap,
  MarkerType, Handle, Position,
  type Node, type Edge, type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent } from '@/components/ui/card';

/* ─── Types ─────────────────────────────────────────────── */
interface TopologyNode { id: string; type: string; label: string; layer?: number; }
interface TopologyEdge { source: string; target: string; }
interface TopologyData { nodes: TopologyNode[]; edges: TopologyEdge[]; }

/* ─── Visual config per node type ────────────────────────── */
const TYPE_STYLE: Record<string, { bg: string; border: string; label: string; dot: string }> = {
  ui:        { bg: '#f0f9ff', border: '#7dd3fc', label: '#0369a1', dot: '#38bdf8' },
  service:   { bg: '#f0fdf4', border: '#86efac', label: '#15803d', dot: '#22c55e' },
  platform:  { bg: '#eef2ff', border: '#a5b4fc', label: '#3730a3', dot: '#6366f1' },
  sre:       { bg: '#fdf4ff', border: '#e879f9', label: '#7e22ce', dot: '#c026d3' },
  ai:        { bg: '#fffbeb', border: '#fbbf24', label: '#92400e', dot: '#f59e0b' },
  execution: { bg: '#fff7ed', border: '#fb923c', label: '#9a3412', dot: '#ea580c' },
  chaos:     { bg: '#fef2f2', border: '#f87171', label: '#991b1b', dot: '#dc2626' },
  datastore: { bg: '#f8fafc', border: '#94a3b8', label: '#334155', dot: '#64748b' },
};

/* ─── Custom node with Handles (required for edges) ─────── */
const ServiceNode = ({ data }: NodeProps) => {
  const s = TYPE_STYLE[(data as any).nodeType] ?? TYPE_STYLE.service;
  return (
    <>
      <Handle type="target" position={Position.Top} style={{ background: s.dot, width: 7, height: 7, border: 'none' }} />
      <div
        style={{
          background: s.bg,
          border: `1.5px solid ${s.border}`,
          borderRadius: 8,
          padding: '6px 12px',
          minWidth: 110,
          maxWidth: 150,
          textAlign: 'center',
          boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
          <span style={{ fontSize: 11, fontWeight: 600, color: s.label, fontFamily: 'Inter, sans-serif', lineHeight: 1.2 }}>
            {(data as any).label}
          </span>
        </div>
        <span style={{ fontSize: 9, color: '#94a3b8', marginTop: 2, display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {(data as any).nodeType}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: s.dot, width: 7, height: 7, border: 'none' }} />
    </>
  );
};

const nodeTypes = { custom: ServiceNode };

/* ─── Layout: 8 horizontal lanes ─────────────────────────── */
// Nodes are bucketed by layer and evenly spaced horizontally within each lane.
const LAYER_Y: Record<number, number> = { 0: 20, 1: 120, 2: 240, 3: 380, 4: 510, 5: 640, 6: 780, 7: 920 };

function computePositions(nodes: TopologyNode[]): Record<string, { x: number; y: number }> {
  // Group by layer
  const layers: Record<number, string[]> = {};
  nodes.forEach((n) => {
    const l = n.layer ?? 0;
    if (!layers[l]) layers[l] = [];
    layers[l].push(n.id);
  });

  const positions: Record<string, { x: number; y: number }> = {};
  const canvasWidth = 1300;

  Object.entries(layers).forEach(([layerStr, ids]) => {
    const layer = Number(layerStr);
    const y = LAYER_Y[layer] ?? layer * 130;
    const spacing = canvasWidth / (ids.length + 1);
    ids.forEach((id, i) => {
      positions[id] = { x: spacing * (i + 1) - 65, y };
    });
  });

  return positions;
}

/* ─── Edge style factory ─────────────────────────────────── */
function makeEdge(e: TopologyEdge, idx: number): Edge {
  return {
    id: `e-${e.source}-${e.target}-${idx}`,
    source: e.source,
    target: e.target,
    animated: false,
    style: { stroke: '#cbd5e1', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8', width: 12, height: 12 },
  };
}

/* ─── Legend entry ───────────────────────────────────────── */
const LegendDot = ({ color, label }: { color: string; label: string }) => (
  <div className="flex items-center gap-1.5">
    <div style={{ width: 9, height: 9, borderRadius: '50%', background: color }} />
    <span className="text-xs text-slate-500 capitalize">{label}</span>
  </div>
);

const LEGEND = Object.entries(TYPE_STYLE).map(([type, s]) => ({ type, color: s.dot }));

/* ─── Page component ─────────────────────────────────────── */
export const LiveTopology = () => {
  const { data, isLoading, error } = useQuery<TopologyData>({
    queryKey: ['topology'],
    queryFn: async () => { const res = await apiClient.get('/topology'); return res.data; },
    refetchInterval: 10000,
  });

  const { nodes, edges } = useMemo<{ nodes: Node[]; edges: Edge[] }>(() => {
    if (!data) return { nodes: [], edges: [] };

    const positions = computePositions(data.nodes);

    const rfNodes: Node[] = data.nodes.map((n) => ({
      id: n.id,
      type: 'custom',
      position: positions[n.id] ?? { x: 0, y: 0 },
      data: { label: n.label, nodeType: n.type },
    }));

    const rfEdges: Edge[] = data.edges.map((e, idx) => makeEdge(e, idx));

    return { nodes: rfNodes, edges: rfEdges };
  }, [data]);

  return (
    <div className="flex flex-col gap-3" style={{ height: 'calc(100vh - 128px)' }}>
      {/* Legend + stats row */}
      <div className="flex items-center gap-4 flex-wrap shrink-0">
        {LEGEND.map(({ type, color }) => (
          <LegendDot key={type} color={color} label={type} />
        ))}
        {data && (
          <div className="ml-auto flex items-center gap-4">
            <span className="text-xs font-num text-slate-400">{data.nodes.length} services</span>
            <span className="text-xs font-num text-slate-400">{data.edges.length} connections</span>
            <span className="text-xs text-slate-300">|</span>
            <span className="text-xs text-slate-400">Drag · Scroll to zoom</span>
          </div>
        )}
      </div>

      {/* Canvas */}
      <Card className="flex-1 overflow-hidden p-0 border-slate-200">
        <CardContent className="h-full p-0">
          {isLoading && (
            <div className="h-full flex items-center justify-center">
              <p className="text-sm text-slate-400 animate-pulse">Building topology graph…</p>
            </div>
          )}
          {error && (
            <div className="h-full flex items-center justify-center">
              <p className="text-sm text-red-500">Failed to load topology -- is dashboard-bff running?</p>
            </div>
          )}
          {nodes.length > 0 && (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.12 }}
              minZoom={0.2}
              maxZoom={2}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#e2e8f0" gap={24} size={1} />
              <Controls style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
              <MiniMap
                nodeColor={(n) => TYPE_STYLE[(n.data as any).nodeType]?.dot ?? '#94a3b8'}
                style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}
                maskColor="rgba(248,250,252,0.7)"
              />
            </ReactFlow>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
