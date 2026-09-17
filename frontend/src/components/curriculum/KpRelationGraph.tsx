"use client";

import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";

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
  前置知识: "#f59e0b",
  后置知识: "#3b82f6",
  相关: "#10b981",
  包含: "#8b5cf6",
};

/** 知识点关系图（cytoscape 力导向），点击节点回调。 */
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
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    el.innerHTML = "";
    const cy = cytoscape({
      container: el,
      elements: {
        nodes: nodes.map((n) => ({
          data: { id: n.id, label: n.name },
        })),
        edges: edges.map((e, i) => ({
          data: {
            id: `e${i}`,
            source: e.source,
            target: e.target,
            relation: e.relation,
          },
        })),
      },
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": "11px",
            color: "#334155",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "96px",
            width: "34px",
            height: "34px",
            "background-color": "#38bdf8",
            "border-width": "0px",
          },
        },
        {
          selector: "edge",
          style: {
            width: "1.5px",
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#94a3b8",
            "line-color": "#94a3b8",
            label: "data(relation)",
            "font-size": "9px",
            color: "#64748b",
            "text-rotation": "autorotate",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.75,
            "text-background-padding": "2px",
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 20 },
    });
    cyRef.current = cy;
    // 边按关系着色
    cy.edges().forEach((edge) => {
      const rel = edge.data("relation") as string;
      const color = RELATION_COLOR[rel] || "#94a3b8";
      edge.style({ "line-color": color, "target-arrow-color": color });
    });
    if (onNodeClick) {
      cy.on("tap", "node", (evt) => onNodeClick(evt.target.id()));
    }
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  return (
    <div
      ref={containerRef}
      data-testid="kp-relation-graph"
      style={{ height }}
      className="w-full rounded-lg border bg-background"
    />
  );
}
