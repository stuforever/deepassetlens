/**
 * 知识点关系图（等价替换原仓 cytoscape 版：tupu 技术栈约束下以纯 SVG +
 * 确定性力导向布局实现，视觉语义 1:1——34px 天蓝圆节点、按关系着色的
 * 带箭头边、边上关系标签（白底、随边旋转）、点击节点回调）。
 */
import { useMemo } from 'react';

export interface KpGraphNode {
  id: string;
  name: string;
  subject?: string;
}
export interface KpGraphEdge {
  source: string;
  target: string;
  relation: string;
}

const RELATION_COLOR: Record<string, string> = {
  前置知识: '#f59e0b',
  后置知识: '#3b82f6',
  相关: '#10b981',
  包含: '#8b5cf6',
};

const W = 640;
const H = 240;

/** 确定性力导向布局（斥力 + 边弹簧 + 弱向心，200 轮迭代）。 */
function computeLayout(nodes: KpGraphNode[], edges: KpGraphEdge[]): Map<string, { x: number; y: number }> {
  const pos = new Map<string, { x: number; y: number }>();
  const n = nodes.length;
  if (!n) return pos;
  nodes.forEach((_, i) => {
    const a = (2 * Math.PI * i) / n - Math.PI / 2;
    pos.set(nodes[i].id, {
      x: W / 2 + (W / 2 - 70) * Math.cos(a),
      y: H / 2 + (H / 2 - 46) * Math.sin(a),
    });
  });
  const idx = new Map(nodes.map((nd, i) => [nd.id, i]));
  const ITER = 200;
  for (let it = 0; it < ITER; it++) {
    const fx = new Array(n).fill(0);
    const fy = new Array(n).fill(0);
    for (let a = 0; a < n; a++) {
      for (let b = a + 1; b < n; b++) {
        let dx = pos.get(nodes[a].id)!.x - pos.get(nodes[b].id)!.x;
        let dy = pos.get(nodes[a].id)!.y - pos.get(nodes[b].id)!.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) {
          // 确定性微扰，避免重合死锁
          dx = (a - b) % 2 === 0 ? 1 : -1;
          dy = 0.5;
          d2 = dx * dx + dy * dy;
        }
        const d = Math.sqrt(d2);
        const f = 26000 / d2;
        fx[a] += (dx / d) * f;
        fy[a] += (dy / d) * f;
        fx[b] -= (dx / d) * f;
        fy[b] -= (dy / d) * f;
      }
    }
    edges.forEach((e) => {
      const a = idx.get(e.source);
      const b = idx.get(e.target);
      if (a == null || b == null) return;
      const dx = pos.get(nodes[b].id)!.x - pos.get(nodes[a].id)!.x;
      const dy = pos.get(nodes[b].id)!.y - pos.get(nodes[a].id)!.y;
      const d = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const f = (d - 110) * 0.02;
      fx[a] += (dx / d) * f;
      fy[a] += (dy / d) * f;
      fx[b] -= (dx / d) * f;
      fy[b] -= (dy / d) * f;
    });
    for (let a = 0; a < n; a++) {
      const p = pos.get(nodes[a].id)!;
      fx[a] += (W / 2 - p.x) * 0.01;
      fy[a] += (H / 2 - p.y) * 0.01;
      const dx = Math.max(-10, Math.min(10, fx[a] * 0.5));
      const dy = Math.max(-10, Math.min(10, fy[a] * 0.5));
      p.x = Math.max(34, Math.min(W - 34, p.x + dx));
      p.y = Math.max(24, Math.min(H - 24, p.y + dy));
    }
  }
  return pos;
}

/** 名称拆两行（>6 字时），近似 cytoscape 的 text-wrap。 */
function splitLabel(name: string): [string] | [string, string] {
  if (name.length > 6) {
    const mid = Math.ceil(name.length / 2);
    return [name.slice(0, mid), name.slice(mid)];
  }
  return [name];
}

export function KpRelationGraph({
  nodes,
  edges,
  onNodeClick,
  height = 260,
}: {
  nodes: KpGraphNode[];
  edges: KpGraphEdge[];
  onNodeClick?: (id: string) => void;
  height?: number;
}) {
  const pos = useMemo(() => computeLayout(nodes, edges), [nodes, edges]);

  // 箭头 marker 按关系色分组（cytoscape 版把箭头染成关系色）
  const markerColors = useMemo(() => {
    const set = new Set<string>(['#94a3b8']);
    edges.forEach((e) => set.add(RELATION_COLOR[e.relation] || '#94a3b8'));
    return Array.from(set);
  }, [edges]);

  return (
    <div
      data-testid="kp-relation-graph"
      style={{ height, width: '100%', borderRadius: 8, border: '1px solid #f0f0f0', background: '#fff' }}
    >
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
        <defs>
          {markerColors.map((c) => (
            <marker
              key={c}
              id={`kp-arrow-${c.replace('#', '')}`}
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 z" fill={c} />
            </marker>
          ))}
        </defs>
        {edges.map((e, i) => {
          const s = pos.get(e.source);
          const t = pos.get(e.target);
          if (!s || !t) return null;
          const color = RELATION_COLOR[e.relation] || '#94a3b8';
          const mx = (s.x + t.x) / 2;
          const my = (s.y + t.y) / 2;
          let ang = (Math.atan2(t.y - s.y, t.x - s.x) * 180) / Math.PI;
          if (ang > 90 || ang < -90) ang += 180; // autorotate：保持标签可读
          return (
            <g key={`e${i}`}>
              <line
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={color}
                strokeWidth={1.5}
                markerEnd={`url(#kp-arrow-${color.replace('#', '')})`}
              />
              <text
                x={mx}
                y={my - 3}
                textAnchor="middle"
                fontSize={9}
                fill="#64748b"
                transform={`rotate(${ang} ${mx} ${my})`}
                style={{ paintOrder: 'stroke', stroke: '#ffffff', strokeWidth: 3, userSelect: 'none' }}
              >
                {e.relation}
              </text>
            </g>
          );
        })}
        {nodes.map((n) => {
          const p = pos.get(n.id);
          if (!p) return null;
          const lines = splitLabel(n.name);
          return (
            <g
              key={n.id}
              onClick={() => onNodeClick && onNodeClick(n.id)}
              style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
            >
              <circle cx={p.x} cy={p.y} r={17} fill="#38bdf8" strokeWidth={0} />
              {lines.length === 1 ? (
                <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={11} fill="#334155" style={{ userSelect: 'none' }}>
                  {lines[0]}
                </text>
              ) : (
                <>
                  <text x={p.x} y={p.y - 1} textAnchor="middle" fontSize={11} fill="#334155" style={{ userSelect: 'none' }}>
                    {lines[0]}
                  </text>
                  <text x={p.x} y={p.y + 11} textAnchor="middle" fontSize={11} fill="#334155" style={{ userSelect: 'none' }}>
                    {lines[1]}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default KpRelationGraph;
