/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/memory/MemoryGraph.tsx，989 行）。
 * 替换点：
 *  - 删除 "use client"；@/lib/memory-graph → 组内 ./memory-graph（数据层随之移植，
 *    自绘 SVG 无 cytoscape/d3 依赖，逐字保留）；
 *  - next/link（Header 回 /memory）→ props.onNavigate("/memory")（路径形状保留，宿主切 tab）；
 *  - lucide → @ant-design/icons：ArrowLeft→ArrowLeftOutlined、Eye→EyeOutlined、
 *    EyeOff→EyeInvisibleOutlined、Loader2→LoadingOutlined、Maximize2→FullscreenOutlined、
 *    RefreshCw→ReloadOutlined、ZoomIn→ZoomInOutlined、ZoomOut→ZoomOutOutlined；
 *  - react-i18next → 组内 zhT.t；Tailwind → 内联样式；hover:/active: 省略登记；
 *    line-clamp-6 → WebkitLineClamp。
 * 平移/缩放/悬停/锁定交互、SVG 结构逐字未改。
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type Dispatch,
  type SetStateAction,
  type WheelEvent as ReactWheelEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  ArrowLeftOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  FullscreenOutlined,
  LoadingOutlined,
  ReloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from "@ant-design/icons";

import {
  buildGraph,
  DEFAULT_LAYOUT,
  fetchMemorySnapshot,
  L3_LABEL,
  SURFACE_LABEL,
  type ClusterMeta,
  type GraphEdge,
  type GraphNode,
  type Layer,
  type MemoryGraph,
} from "./memory-graph";
import { t } from "./zhT";

interface ViewState {
  scale: number;
  tx: number;
  ty: number;
}

interface HoverState {
  node: GraphNode;
  containerLeft: number;
  containerTop: number;
}

const INITIAL_VIEW: ViewState = { scale: 1, tx: 0, ty: 0 };

// One canonical hue per layer; alpha is per-state (idle/hover/dim).
// Drawn from DeepTutor's primary palette so dark mode stays warm too.
const LAYER_COLOR: Record<Layer, string> = {
  L3: "var(--primary, #1677ff)",
  L2: "color-mix(in srgb, var(--primary, #1677ff) 78%, var(--foreground, rgba(0,0,0,0.88)) 22%)",
  L1: "color-mix(in srgb, var(--primary, #1677ff) 38%, var(--foreground, rgba(0,0,0,0.88)) 62%)",
};

const RING_LINE: Record<Layer, string> = {
  L3: "color-mix(in srgb, var(--primary, #1677ff) 22%, transparent)",
  L2: "color-mix(in srgb, var(--primary, #1677ff) 14%, transparent)",
  L1: "color-mix(in srgb, var(--foreground, rgba(0,0,0,0.88)) 10%, transparent)",
};

export interface MemoryGraphProps {
  onNavigate?: (path: string) => void;
}

export function MemoryGraph({ onNavigate }: MemoryGraphProps = {}) {
  const [graph, setGraph] = useState<MemoryGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [layerOn, setLayerOn] = useState<Record<Layer, boolean>>({
    L1: true,
    L2: true,
    L3: true,
  });
  const [hover, setHover] = useState<HoverState | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<ViewState>(INITIAL_VIEW);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origTx: number;
    origTy: number;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const snap = await fetchMemorySnapshot();
      setGraph(buildGraph(snap));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // ── Derived: active node id used by hover *or* explicit selection.
  const activeId = selected ?? hover?.node.id ?? null;

  const highlight = useMemo(() => {
    if (!graph || !activeId) return null;
    const neighbours = new Set<string>([activeId]);
    const queue = [activeId];
    // BFS limited to 2 hops so we get e.g. L3 → L2 → L1 chains.
    for (let depth = 0; depth < 2 && queue.length; depth++) {
      const next: string[] = [];
      for (const id of queue) {
        const adj = graph.adjacency.get(id) ?? [];
        for (const n of adj) {
          if (!neighbours.has(n)) {
            neighbours.add(n);
            next.push(n);
          }
        }
      }
      queue.length = 0;
      queue.push(...next);
    }
    return neighbours;
  }, [graph, activeId]);

  // ── Pan / zoom handlers.
  const onWheel = useCallback((e: ReactWheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setView((v) => {
      const factor = Math.exp(-e.deltaY * 0.001);
      const next = Math.min(4, Math.max(0.35, v.scale * factor));
      // Zoom centered on cursor: keep the world point under the cursor stationary.
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;
      const k = next / v.scale;
      const tx = px - k * (px - v.tx);
      const ty = py - k * (py - v.ty);
      return { scale: next, tx, ty };
    });
  }, []);

  const onPointerDown = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      // Only start a drag on background clicks — let node clicks bubble.
      if ((e.target as HTMLElement).closest("[data-node]")) return;
      (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
      dragRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        origTx: view.tx,
        origTy: view.ty,
      };
      setSelected(null);
    },
    [view],
  );

  const onPointerMove = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    const d = dragRef.current;
    if (!d || d.pointerId !== e.pointerId) return;
    setView((v) => ({
      ...v,
      tx: d.origTx + (e.clientX - d.startX),
      ty: d.origTy + (e.clientY - d.startY),
    }));
  }, []);

  const endDrag = useCallback(() => {
    dragRef.current = null;
  }, []);

  const showNodeHover = useCallback((node: GraphNode) => {
    const rect = containerRef.current?.getBoundingClientRect();
    setHover({
      node,
      containerLeft: rect?.left ?? 0,
      containerTop: rect?.top ?? 0,
    });
  }, []);

  // ── Center / fit the graph to the container on first paint.
  useEffect(() => {
    if (!graph) return;
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const target = DEFAULT_LAYOUT.width;
    const scale = Math.min(rect.width / target, rect.height / target) * 0.95;
    setView({
      scale,
      tx: (rect.width - target * scale) / 2,
      ty: (rect.height - target * scale) / 2,
    });
  }, [graph]);

  const fit = useCallback(() => {
    if (!graph) return;
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const target = DEFAULT_LAYOUT.width;
    const scale = Math.min(rect.width / target, rect.height / target) * 0.95;
    setView({
      scale,
      tx: (rect.width - target * scale) / 2,
      ty: (rect.height - target * scale) / 2,
    });
  }, [graph]);

  const zoomBy = useCallback((factor: number) => {
    const el = containerRef.current;
    const rect = el?.getBoundingClientRect();
    if (!rect) return;
    setView((v) => {
      const next = Math.min(4, Math.max(0.35, v.scale * factor));
      const px = rect.width / 2;
      const py = rect.height / 2;
      const k = next / v.scale;
      return {
        scale: next,
        tx: px - k * (px - v.tx),
        ty: py - k * (py - v.ty),
      };
    });
  }, []);

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 0, flexDirection: "column" }}>
      <Header onRefresh={() => void load()} loading={loading} onNavigate={onNavigate} />

      <div style={{ position: "relative", flex: 1, minHeight: 0, overflow: "hidden" }}>
        <div
          ref={containerRef}
          onWheel={onWheel}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          style={{
            position: "absolute",
            inset: 0,
            cursor: "grab",
            touchAction: "none",
            userSelect: "none",
            background:
              "radial-gradient(ellipse at center, color-mix(in srgb, var(--primary, #1677ff) 7%, var(--background, #ffffff)) 0%, var(--background, #ffffff) 65%)",
          }}
        >
          {graph && (
            <GraphView
              graph={graph}
              view={view}
              layerOn={layerOn}
              hover={hover}
              showNodeHover={showNodeHover}
              setHover={setHover}
              selected={selected}
              setSelected={setSelected}
              highlight={highlight}
            />
          )}

          {loading && (
            <div
              style={{
                pointerEvents: "none",
                position: "absolute",
                inset: 0,
                display: "grid",
                placeItems: "center",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  borderRadius: 999,
                  border: "1px solid var(--border, #d9d9d9)",
                  background: "color-mix(in srgb, var(--card, #ffffff) 80%, transparent)",
                  padding: "6px 12px",
                  fontSize: 12,
                  color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                  backdropFilter: "blur(4px)",
                }}
              >
                <LoadingOutlined style={{ fontSize: 14 }} />
                {t("Composing memory graph…")}
              </div>
            </div>
          )}

          {graph && !loading && (
            <Controls
              view={view}
              layerOn={layerOn}
              setLayerOn={setLayerOn}
              zoomBy={zoomBy}
              fit={fit}
            />
          )}

          {hover && <HoverCard hover={hover} view={view} />}
        </div>

        {graph && !loading && <Legend graph={graph} />}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────── Header

function Header({
  onRefresh,
  loading,
  onNavigate,
}: {
  onRefresh: () => void;
  loading: boolean;
  onNavigate?: (path: string) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid var(--border, #d9d9d9)",
        background: "color-mix(in srgb, var(--background, #ffffff) 80%, transparent)",
        padding: "12px 24px",
        backdropFilter: "blur(4px)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          type="button"
          onClick={() => onNavigate?.("/memory")}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            borderRadius: 6,
            border: "1px solid var(--border, #d9d9d9)",
            background: "var(--background, #ffffff)",
            padding: "4px 10px",
            fontSize: 12,
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
            cursor: "pointer",
          }}
        >
          <ArrowLeftOutlined style={{ fontSize: 14 }} />
          {t("Memory")}
        </button>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <h1
            style={{
              fontSize: 16,
              fontWeight: 600,
              letterSpacing: "-0.01em",
              color: "var(--foreground, rgba(0,0,0,0.88))",
              margin: 0,
              fontFamily: "Georgia, 'Times New Roman', serif",
            }}
          >
            {t("Memory graph")}
          </h1>
          <p
            style={{
              fontSize: 11.5,
              color: "var(--muted-foreground, rgba(0,0,0,0.45))",
              margin: 0,
            }}
          >
            {t(
              "L3 synthesis at the centre, L2 facts in the middle ring, L1 traces on the outside.",
            )}
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onRefresh}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          borderRadius: 6,
          border: "1px solid var(--border, #d9d9d9)",
          background: "var(--background, #ffffff)",
          padding: "4px 10px",
          fontSize: 12,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          cursor: loading ? "not-allowed" : "pointer",
          opacity: loading ? 0.5 : 1,
        }}
        disabled={loading}
      >
        <LoadingOutlined
          style={{ fontSize: 14 }}
          spin={loading}
        />
        {t("Refresh")}
      </button>
    </div>
  );
}

// ───────────────────────────────────────────────────────── GraphView

interface GraphViewProps {
  graph: MemoryGraph;
  view: ViewState;
  layerOn: Record<Layer, boolean>;
  hover: HoverState | null;
  showNodeHover: (node: GraphNode) => void;
  setHover: Dispatch<SetStateAction<HoverState | null>>;
  selected: string | null;
  setSelected: Dispatch<SetStateAction<string | null>>;
  highlight: Set<string> | null;
}

function GraphView({
  graph,
  view,
  layerOn,
  hover,
  showNodeHover,
  setHover,
  selected,
  setSelected,
  highlight,
}: GraphViewProps) {
  // ── Cluster halos: large blurred translucent ellipses behind each
  // slice so users see the cluster outlines before they read labels.
  const haloPaths = useMemo(() => {
    return graph.clusters.map((c) => buildClusterArc(c));
  }, [graph.clusters]);

  const visibleEdges = useMemo(() => {
    return graph.edges.filter((e) => {
      const sLayer = e.source.startsWith("L1")
        ? "L1"
        : e.source.startsWith("L2")
          ? "L2"
          : "L3";
      const tLayer = e.target.startsWith("L1")
        ? "L1"
        : e.target.startsWith("L2")
          ? "L2"
          : "L3";
      return layerOn[sLayer as Layer] && layerOn[tLayer as Layer];
    });
  }, [graph.edges, layerOn]);

  // Pre-index nodes by id for fast endpoint lookup when drawing edges.
  const nodeIdx = useMemo(() => {
    const m = new Map<string, GraphNode>();
    for (const n of graph.nodes) m.set(n.id, n);
    return m;
  }, [graph.nodes]);

  return (
    <svg
      width="100%"
      height="100%"
      style={{ position: "absolute", inset: 0 }}
      aria-label={t("Memory graph")}
    >
      <defs>
        <radialGradient id="halo-l3" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.20" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.02" />
        </radialGradient>
        <radialGradient id="halo-l2" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.12" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.02" />
        </radialGradient>
        <radialGradient id="halo-l1" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--foreground)" stopOpacity="0.08" />
          <stop
            offset="100%"
            stopColor="var(--foreground)"
            stopOpacity="0.01"
          />
        </radialGradient>
      </defs>

      <g transform={`translate(${view.tx} ${view.ty}) scale(${view.scale})`}>
        {/* Concentric ring guides (faint). */}
        <g pointerEvents="none">
          {(["L1", "L2", "L3"] as const).map((layer) => {
            if (!layerOn[layer]) return null;
            const opt = DEFAULT_LAYOUT;
            const inner =
              layer === "L1"
                ? opt.l1InnerRadius
                : layer === "L2"
                  ? opt.l2InnerRadius
                  : opt.l3InnerRadius;
            const outer =
              layer === "L1"
                ? opt.l1OuterRadius
                : layer === "L2"
                  ? opt.l2OuterRadius
                  : opt.l3OuterRadius;
            const cx = opt.width / 2;
            const cy = opt.height / 2;
            return (
              <g key={`ring-${layer}`}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={inner}
                  fill="none"
                  stroke={RING_LINE[layer]}
                  strokeWidth={0.6}
                  strokeDasharray="2 3"
                />
                <circle
                  cx={cx}
                  cy={cy}
                  r={outer}
                  fill="none"
                  stroke={RING_LINE[layer]}
                  strokeWidth={0.6}
                  strokeDasharray="2 3"
                />
              </g>
            );
          })}
        </g>

        {/* Cluster halos. */}
        <g pointerEvents="none">
          {graph.clusters.map((c, i) => {
            if (!layerOn[c.layer]) return null;
            const fill = `url(#halo-${c.layer.toLowerCase()})`;
            return (
              <path
                key={c.id}
                d={haloPaths[i]}
                fill={fill}
                stroke="color-mix(in srgb, var(--primary) 8%, transparent)"
                strokeWidth={0.6}
              />
            );
          })}
        </g>

        {/* Cluster labels. L1 labels orbit *outside* the outer ring,
           L2 labels sit just outside the L2 ring, L3 labels are
           rendered as a single core badge (handled below). */}
        <g pointerEvents="none">
          {graph.clusters.map((c) => {
            if (!layerOn[c.layer]) return null;
            if (c.layer === "L3") return null;
            const mid = (c.startAngle + c.endAngle) / 2;
            const cx = DEFAULT_LAYOUT.width / 2;
            const cy = DEFAULT_LAYOUT.height / 2;
            const rOut = c.outerRadius + (c.layer === "L1" ? 30 : 18);
            const x = cx + Math.cos(mid) * rOut;
            const y = cy + Math.sin(mid) * rOut;
            return (
              <g key={`label-${c.id}`}>
                <text
                  x={x}
                  y={y - 12}
                  fontSize={c.layer === "L2" ? 20 : 22}
                  fontWeight={600}
                  fill="var(--foreground)"
                  textAnchor="middle"
                  dominantBaseline="central"
                  style={{ userSelect: "none" }}
                >
                  {t(c.label)}
                </text>
                <text
                  x={x}
                  y={y + 14}
                  fontSize={15}
                  fontWeight={500}
                  fill="var(--muted-foreground)"
                  textAnchor="middle"
                  dominantBaseline="central"
                  style={{ userSelect: "none" }}
                >
                  {c.count.toLocaleString()}{" "}
                  {c.layer === "L2" ? t("facts") : t("traces")}
                </text>
              </g>
            );
          })}
        </g>

        {/* L3 core: a soft "core" plate at the centre with the three
           slot labels placed at their slice mid-angles inside the
           inner radius. */}
        {layerOn.L3 && (
          <g pointerEvents="none">
            <circle
              cx={DEFAULT_LAYOUT.width / 2}
              cy={DEFAULT_LAYOUT.height / 2}
              r={DEFAULT_LAYOUT.l3InnerRadius - 6}
              fill="color-mix(in srgb, var(--primary) 12%, var(--background))"
              stroke="color-mix(in srgb, var(--primary) 22%, transparent)"
              strokeWidth={1}
            />
            <text
              x={DEFAULT_LAYOUT.width / 2}
              y={DEFAULT_LAYOUT.height / 2 - 10}
              fontSize={22}
              fontWeight={700}
              fill="var(--primary)"
              textAnchor="middle"
              dominantBaseline="central"
              style={{ letterSpacing: "0.08em", userSelect: "none" }}
            >
              L3
            </text>
            <text
              x={DEFAULT_LAYOUT.width / 2}
              y={DEFAULT_LAYOUT.height / 2 + 16}
              fontSize={14}
              fontWeight={500}
              fill="var(--muted-foreground)"
              textAnchor="middle"
              dominantBaseline="central"
              style={{ letterSpacing: "0.04em", userSelect: "none" }}
            >
              {t("synthesis")}
            </text>
            {graph.clusters
              .filter((c) => c.layer === "L3")
              .map((c) => {
                const mid = (c.startAngle + c.endAngle) / 2;
                const cx = DEFAULT_LAYOUT.width / 2;
                const cy = DEFAULT_LAYOUT.height / 2;
                const r = c.outerRadius + 14;
                const x = cx + Math.cos(mid) * r;
                const y = cy + Math.sin(mid) * r;
                return (
                  <text
                    key={`l3-label-${c.id}`}
                    x={x}
                    y={y}
                    fontSize={18}
                    fontWeight={600}
                    fill="var(--primary)"
                    textAnchor="middle"
                    dominantBaseline="central"
                    style={{ letterSpacing: "0.04em", userSelect: "none" }}
                  >
                    {t(c.label)}
                  </text>
                );
              })}
          </g>
        )}

        {/* Edges. */}
        <g pointerEvents="none">
          {visibleEdges.map((e) => {
            const s = nodeIdx.get(e.source);
            const t2 = nodeIdx.get(e.target);
            if (!s || !t2) return null;
            const dim =
              highlight !== null &&
              !highlight.has(e.source) &&
              !highlight.has(e.target);
            const focused =
              highlight !== null &&
              highlight.has(e.source) &&
              highlight.has(e.target);
            const opacity = dim
              ? 0.04
              : focused
                ? e.kind === "strong"
                  ? 0.85
                  : 0.55
                : e.kind === "strong"
                  ? 0.16
                  : 0.08;
            const stroke = focused ? "var(--primary)" : LAYER_COLOR[layerOf(e)];
            return (
              <EdgePath
                key={`${e.source}->${e.target}`}
                edge={e}
                s={s}
                t={t2}
                opacity={opacity}
                stroke={stroke}
                focused={focused}
              />
            );
          })}
        </g>

        {/* Nodes. */}
        <g>
          {graph.nodes.map((n) => {
            if (!layerOn[n.layer]) return null;
            if (n.r === 0) return null; // synthetic anchor
            const dim = highlight !== null && !highlight.has(n.id);
            const focused = highlight !== null && highlight.has(n.id);
            const isActive = n.id === (selected ?? hover?.node.id);
            return (
              <NodeDot
                key={n.id}
                node={n}
                isActive={isActive}
                focused={focused}
                dim={dim}
                onEnter={showNodeHover}
                onLeave={(node) =>
                  setHover((cur) => (cur?.node.id === node.id ? null : cur))
                }
                onClick={() =>
                  setSelected((cur) => (cur === n.id ? null : n.id))
                }
              />
            );
          })}
        </g>
      </g>
    </svg>
  );
}

function layerOf(e: GraphEdge): Layer {
  // Pick the more synthetic layer for edge colour: L3 dominates,
  // then L2.
  if (e.source.startsWith("L3") || e.target.startsWith("L3")) return "L3";
  if (e.source.startsWith("L2") || e.target.startsWith("L2")) return "L2";
  return "L1";
}

function EdgePath({
  edge,
  s,
  t,
  opacity,
  stroke,
  focused,
}: {
  edge: GraphEdge;
  s: GraphNode;
  t: GraphNode;
  opacity: number;
  stroke: string;
  focused: boolean;
}) {
  // Quadratic curve: control point pulled toward the canvas center
  // gives the bundle a hub-and-spoke feel rather than a noisy mesh.
  const cx = DEFAULT_LAYOUT.width / 2;
  const cy = DEFAULT_LAYOUT.height / 2;
  const mx = (s.x + t.x) / 2;
  const my = (s.y + t.y) / 2;
  const k = edge.kind === "soft" ? 0.45 : 0.25;
  const cpx = mx + (cx - mx) * k;
  const cpy = my + (cy - my) * k;
  return (
    <path
      d={`M ${s.x} ${s.y} Q ${cpx} ${cpy} ${t.x} ${t.y}`}
      stroke={stroke}
      strokeWidth={focused ? 0.9 : edge.kind === "strong" ? 0.5 : 0.35}
      strokeOpacity={opacity}
      fill="none"
      strokeLinecap="round"
    />
  );
}

function NodeDot({
  node,
  isActive,
  focused,
  dim,
  onEnter,
  onLeave,
  onClick,
}: {
  node: GraphNode;
  isActive: boolean;
  focused: boolean;
  dim: boolean;
  onEnter: (node: GraphNode) => void;
  onLeave: (node: GraphNode) => void;
  onClick: () => void;
}) {
  const baseR = node.r;
  const r = isActive ? baseR * 2.1 : focused ? baseR * 1.35 : baseR;
  const fill = LAYER_COLOR[node.layer];
  const opacity = dim ? 0.18 : 1;
  // Always offer at least a 10-pixel-radius invisible target so the
  // mouse doesn't need pixel-perfect aim. Larger of (3×base radius,
  // 10px) gives small L1 dots a generous hit halo without making
  // dense clusters fight over hover.
  const hitR = Math.max(baseR * 3, 10);
  return (
    <g data-node={node.id} style={{ cursor: "pointer" }}>
      <circle
        cx={node.x}
        cy={node.y}
        r={hitR}
        fill="transparent"
        pointerEvents="all"
        onPointerEnter={() => onEnter(node)}
        onPointerLeave={() => onLeave(node)}
        onClick={onClick}
      />
      {isActive && (
        <circle
          cx={node.x}
          cy={node.y}
          r={r * 2.5}
          fill={fill}
          opacity={0.18}
          pointerEvents="none"
        />
      )}
      <circle
        cx={node.x}
        cy={node.y}
        r={r}
        fill={fill}
        opacity={opacity}
        stroke={isActive ? "var(--background)" : "transparent"}
        strokeWidth={isActive ? 1.5 : 0}
        pointerEvents="none"
      />
    </g>
  );
}

// Pie-slice "arc" path between two radii.
function buildClusterArc(c: ClusterMeta): string {
  const cx = DEFAULT_LAYOUT.width / 2;
  const cy = DEFAULT_LAYOUT.height / 2;
  const { startAngle, endAngle, innerRadius, outerRadius } = c;
  const large = endAngle - startAngle > Math.PI ? 1 : 0;
  const x1 = cx + Math.cos(startAngle) * outerRadius;
  const y1 = cy + Math.sin(startAngle) * outerRadius;
  const x2 = cx + Math.cos(endAngle) * outerRadius;
  const y2 = cy + Math.sin(endAngle) * outerRadius;
  const x3 = cx + Math.cos(endAngle) * innerRadius;
  const y3 = cy + Math.sin(endAngle) * innerRadius;
  const x4 = cx + Math.cos(startAngle) * innerRadius;
  const y4 = cy + Math.sin(startAngle) * innerRadius;
  return [
    `M ${x1} ${y1}`,
    `A ${outerRadius} ${outerRadius} 0 ${large} 1 ${x2} ${y2}`,
    `L ${x3} ${y3}`,
    `A ${innerRadius} ${innerRadius} 0 ${large} 0 ${x4} ${y4}`,
    "Z",
  ].join(" ");
}

// ─────────────────────────────────────────────────────────── Controls

function Controls({
  view,
  layerOn,
  setLayerOn,
  zoomBy,
  fit,
}: {
  view: ViewState;
  layerOn: Record<Layer, boolean>;
  setLayerOn: (next: Record<Layer, boolean>) => void;
  zoomBy: (factor: number) => void;
  fit: () => void;
}) {
  return (
    <div
      style={{
        pointerEvents: "none",
        position: "absolute",
        right: 16,
        top: 16,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        gap: 8,
      }}
    >
      <div
        style={{
          pointerEvents: "auto",
          display: "inline-flex",
          alignItems: "center",
          overflow: "hidden",
          borderRadius: 8,
          border: "1px solid var(--border, #d9d9d9)",
          background: "color-mix(in srgb, var(--card, #ffffff) 95%, transparent)",
          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          backdropFilter: "blur(4px)",
        }}
      >
        <IconButton onClick={() => zoomBy(1.25)} title={t("Zoom in")}>
          <ZoomInOutlined style={{ fontSize: 14 }} />
        </IconButton>
        <IconButton onClick={() => zoomBy(1 / 1.25)} title={t("Zoom out")}>
          <ZoomOutOutlined style={{ fontSize: 14 }} />
        </IconButton>
        <IconButton onClick={fit} title={t("Fit")}>
          <FullscreenOutlined style={{ fontSize: 14 }} />
        </IconButton>
        <span
          style={{
            padding: "0 8px",
            fontSize: 11,
            fontVariantNumeric: "tabular-nums",
            color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          }}
        >
          {(view.scale * 100).toFixed(0)}%
        </span>
      </div>

      <div
        style={{
          pointerEvents: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 4,
          borderRadius: 8,
          border: "1px solid var(--border, #d9d9d9)",
          background: "color-mix(in srgb, var(--card, #ffffff) 95%, transparent)",
          padding: 6,
          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          backdropFilter: "blur(4px)",
        }}
      >
        {(["L3", "L2", "L1"] as const).map((layer) => (
          <button
            key={layer}
            type="button"
            onClick={() => setLayerOn({ ...layerOn, [layer]: !layerOn[layer] })}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              borderRadius: 6,
              padding: "4px 8px",
              fontSize: 11.5,
              color: "var(--foreground, rgba(0,0,0,0.88))",
              border: "none",
              background: "transparent",
              cursor: "pointer",
            }}
          >
            <span
              style={{
                display: "inline-block",
                height: 8,
                width: 8,
                borderRadius: 999,
                background: LAYER_COLOR[layer],
              }}
            />
            <span style={{ fontWeight: 500 }}>{layer}</span>
            <span style={{ color: "var(--muted-foreground, rgba(0,0,0,0.45))" }}>
              {layer === "L3"
                ? t("Synthesis")
                : layer === "L2"
                  ? t("Per-surface")
                  : t("Raw traces")}
            </span>
            {layerOn[layer] ? (
              <EyeOutlined
                style={{
                  marginLeft: 4,
                  fontSize: 12,
                  color: "var(--muted-foreground, rgba(0,0,0,0.45))",
                }}
              />
            ) : (
              <EyeInvisibleOutlined
                style={{
                  marginLeft: 4,
                  fontSize: 12,
                  color: "color-mix(in srgb, var(--muted-foreground, rgba(0,0,0,0.45)) 60%, transparent)",
                }}
              />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function IconButton({
  onClick,
  title,
  children,
}: {
  onClick: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        display: "grid",
        height: 32,
        width: 32,
        placeItems: "center",
        color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        border: "none",
        background: "transparent",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

// ──────────────────────────────────────────────────────────── Legend

function Legend({ graph }: { graph: MemoryGraph }) {
  // Aggregate counts.
  const byLayer = useMemo(() => {
    const out: Record<Layer, number> = { L1: 0, L2: 0, L3: 0 };
    for (const n of graph.nodes) {
      if (n.r === 0) continue; // ignore synthetic anchors
      out[n.layer] += 1;
    }
    return out;
  }, [graph.nodes]);

  return (
    <div
      style={
        {
          pointerEvents: "none",
          position: "absolute",
          bottom: 16,
          left: 16,
          maxWidth: 448,
          borderRadius: 8,
          border: "1px solid var(--border, #d9d9d9)",
          background: "color-mix(in srgb, var(--card, #ffffff) 92%, transparent)",
          padding: 12,
          fontSize: 11.5,
          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          backdropFilter: "blur(4px)",
        } as CSSProperties
      }
    >
      <div
        style={{
          marginBottom: 8,
          display: "flex",
          alignItems: "center",
          gap: 12,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        {(["L3", "L2", "L1"] as const).map((layer) => (
          <span key={layer} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span
              style={{
                display: "inline-block",
                height: 8,
                width: 8,
                borderRadius: 999,
                background: LAYER_COLOR[layer],
              }}
            />
            <span
              style={{
                fontWeight: 500,
                color: "var(--foreground, rgba(0,0,0,0.88))",
              }}
            >
              {layer}
            </span>
            <span>{byLayer[layer]}</span>
          </span>
        ))}
      </div>
      <p
        style={{
          lineHeight: 1.625,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          margin: 0,
        }}
      >
        {t(
          "Hover a node to preview the memory. Click to lock the highlight and trace its references inward (L1 → L2 → L3) or outward.",
        )}
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────────────── HoverCard

function HoverCard({ hover, view }: { hover: HoverState; view: ViewState }) {
  const { node } = hover;
  // Anchor the tooltip to the *node's* screen position (not the
  // cursor), so we don't have to handle mousemove for every dot. The
  // card is offset down-right of the node so the user can still read
  // the dot underneath the cursor.
  const screenX = hover.containerLeft + node.x * view.scale + view.tx;
  const screenY = hover.containerTop + node.y * view.scale + view.ty;
  const offset = Math.max(node.r * view.scale + 14, 18);
  const style: CSSProperties = {
    left: screenX + offset,
    top: screenY + offset,
  };
  const meta = nodeMeta(node);
  return (
    <div
      style={{
        ...style,
        pointerEvents: "none",
        position: "fixed",
        zIndex: 50,
        maxWidth: 384,
        borderRadius: 8,
        border: "1px solid var(--border, #d9d9d9)",
        background: "var(--card, #ffffff)",
        padding: 12,
        fontSize: 12,
        boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1)",
      }}
    >
      <div
        style={{
          marginBottom: 4,
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 10.5,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
        }}
      >
        <span
          style={{
            display: "inline-block",
            height: 8,
            width: 8,
            borderRadius: 999,
            background: LAYER_COLOR[node.layer],
          }}
        />
        <span>{meta.layerLabel}</span>
        <span style={{ color: "var(--border, #d9d9d9)" }}>·</span>
        <span>{meta.clusterLabel}</span>
        {node.section && (
          <>
            <span style={{ color: "var(--border, #d9d9d9)" }}>·</span>
            <span
              style={{
                color:
                  "color-mix(in srgb, var(--foreground, rgba(0,0,0,0.88)) 80%, transparent)",
              }}
            >
              {node.section}
            </span>
          </>
        )}
      </div>
      <p
        style={{
          lineHeight: 1.625,
          color: "var(--foreground, rgba(0,0,0,0.88))",
          display: "-webkit-box",
          WebkitLineClamp: 6,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
          margin: 0,
        }}
      >
        {node.preview || node.label}
      </p>
      <p
        style={{
          marginTop: 8,
          fontSize: 10.5,
          color: "var(--muted-foreground, rgba(0,0,0,0.45))",
          marginBottom: 0,
        }}
      >
        {t("Click to lock · open in workbench")}
      </p>
    </div>
  );
}

function nodeMeta(n: GraphNode): { layerLabel: string; clusterLabel: string } {
  const [, cluster] = n.cluster.split(":");
  if (n.layer === "L3") {
    return {
      layerLabel: t("L3 · synthesis"),
      clusterLabel: t(L3_LABEL[cluster as keyof typeof L3_LABEL] || cluster),
    };
  }
  if (n.layer === "L2") {
    return {
      layerLabel: t("L2 · curated"),
      clusterLabel: t(
        SURFACE_LABEL[cluster as keyof typeof SURFACE_LABEL] || cluster,
      ),
    };
  }
  return {
    layerLabel: t("L1 · raw trace"),
    clusterLabel: t(
      SURFACE_LABEL[cluster as keyof typeof SURFACE_LABEL] || cluster,
    ),
  };
}

// 原仓末尾 re-export `export type { GraphNode, GraphEdge, MemoryGraph }` 在 tupu
// 移植后与 named 导出的组件 MemoryGraph 同名冲突（TS2323），删除该 re-export（登记）：
// 数据类型改由 ./memory-graph 直接导出，消费方从该模块 import。

export default MemoryGraph;
