"use client";

import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Brain, ChevronDown, ChevronRight, FlaskConical, Lightbulb, Loader2, Network,
} from "lucide-react";
import type { ChapterOverview, KnowledgePointSummary } from "../../../../../lib/self-learning-api";
import { apiUrl } from "../../../../../lib/api";
import MarkdownRenderer from "../../../../../components/common/MarkdownRenderer";
import { KpRelationGraph } from "../../../../../components/curriculum/KpRelationGraph";
import { MathWidget } from "../../../../../components/curriculum/MathWidget";
import { SUBJECT_DISPLAY } from "../../../../../components/mother-questions/MotherQuestionFields";
import { TabExportToolbar } from "../TabExportToolbar";

function DifficultyStars({ d }: { d: number | null | undefined }) {
  const { t } = useTranslation();
  if (!d) return null;
  return (
    <span className="text-[10px] text-amber-500" title={t("Difficulty {{count}}/5", { count: d })}>
      {"★".repeat(Math.min(5, d))}
    </span>
  );
}

/** 自主学习「知识点总结」：知识树轮廓 + 总结/讲解/实例/公式推导/可拖拽图形/相关关系。 */
export function KnowledgePointsTab({ overview, chapterId }: { overview: ChapterOverview; chapterId: string }) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const kps = overview.knowledge_points || [];
  const isMath = overview.textbook.subject === "math";

  const goToKp = async (kid: string) => {
    try {
      const d = await fetch(apiUrl(`/api/v1/curriculum/knowledge-points/${kid}/chapters`)).then((r) => r.json());
      const items = d?.items || [];
      if (items.length > 0) {
        navigate(`/e/tutor/self-learning?chapter_id=${items[0].chapter_id}`);
      }
    } catch {
      // 忽略跳转失败
    }
  };

  const scrollToKp = (id: string) => {
    document.getElementById(`kp-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // 章节内知识点关系图（仅保留目标也在本章内的边）
  const graph = useMemo(() => {
    const nodes = kps.map((k) => ({ id: k.id, name: k.name, subject: k.subject }));
    const edges: { source: string; target: string; relation: string }[] = [];
    const idSet = new Set(kps.map((k) => k.id));
    for (const k of kps) {
      for (const r of k.related || []) {
        if (idSet.has(r.kp_id)) {
          edges.push({ source: k.id, target: r.kp_id, relation: r.relation });
        }
      }
    }
    return { nodes, edges };
  }, [kps]);

  // 知识树轮廓：按祖先链分组
  const outline = useMemo(() => {
    const root: { children: Map<string, OutlineNode>; ids: string[] } = {
      children: new Map(),
      ids: [],
    };
    for (const kp of kps) {
      const parts = kp.path ? kp.path.split(" → ").filter(Boolean) : [];
      let node = root;
      for (const seg of [...parts, kp.name]) {
        if (!node.children.has(seg)) {
          node.children.set(seg, { name: seg, children: new Map(), ids: [], difficulty: seg === kp.name ? kp.difficulty : null });
        }
        node = node.children.get(seg)!;
      }
      node.ids.push(kp.id);
    }
    return root;
  }, [kps]);

  if (kps.length === 0) {
    return (
      <div className="p-4" data-testid="tab-panel-knowledge">
        <div className="p-4 rounded border bg-muted/30 text-center">
          <Brain className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">{t("This chapter has no knowledge points linked yet.")}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {t("You can link knowledge points to this chapter in Settings → Settings management → Chapter management. They will appear here after linking.")}
          </p>
          <a href="/settings/curriculum/chapters" className="inline-block mt-3 text-xs text-primary hover:underline">
            {t("Go to chapter management to link →")}
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3" data-testid="tab-panel-knowledge">
      <TabExportToolbar chapterId={chapterId} tab="knowledge" />
      <div className="text-sm text-muted-foreground">{t("{{count}} knowledge points (sorted by difficulty, easy to hard)", { count: kps.length })}</div>

      {/* 知识树轮廓（所有学科） */}
      <div className="rounded-lg border bg-card p-3">
        <div className="text-xs font-medium text-muted-foreground mb-2">
          {t("🌳 Chapter knowledge tree (click to locate a knowledge point)")}
        </div>
        <OutlineTree root={outline} onPick={scrollToKp} />
      </div>

      {/* 数学章节：知识关系图 */}
      {isMath && graph.edges.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
            <Network className="w-3.5 h-3.5" /> {t("Knowledge relation graph (nodes = knowledge points in this chapter, edges = relation types, click a node to locate)")}
          </div>
          <KpRelationGraph nodes={graph.nodes} edges={graph.edges} onNodeClick={scrollToKp} height={280} />
        </div>
      )}

      {kps.map((kp) => (
        <KpCard key={kp.id} kp={kp} isMath={isMath} onGoToKp={goToKp} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 知识树轮廓
// ---------------------------------------------------------------------------
interface OutlineNode {
  name: string;
  children: Map<string, OutlineNode>;
  ids: string[];
  difficulty?: number | null;
}

function OutlineTree({
  root,
  onPick,
}: {
  root: { children: Map<string, OutlineNode>; ids: string[] };
  onPick: (id: string) => void;
}) {
  return (
    <div className="space-y-0.5 text-sm">
      {[...root.children.values()].map((node) => (
        <OutlineNodeView key={node.name} node={node} depth={0} onPick={onPick} />
      ))}
    </div>
  );
}

function OutlineNodeView({
  node,
  depth,
  onPick,
}: {
  node: OutlineNode;
  depth: number;
  onPick: (id: string) => void;
}) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children.size > 0;
  const isLeaf = !hasChildren;
  return (
    <div>
      <div
        className={`flex items-center gap-1.5 py-0.5 rounded hover:bg-accent/50 cursor-pointer ${
          isLeaf ? "text-foreground" : "font-medium"
        }`}
        style={{ paddingLeft: depth * 14 }}
        onClick={() => {
          if (isLeaf && node.ids.length > 0) onPick(node.ids[0]);
          else setOpen((v) => !v);
        }}
      >
        {hasChildren ? (
          <span className={`transition-transform ${open ? "rotate-90" : ""}`}>
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
          </span>
        ) : (
          <span className="w-3.5" />
        )}
        <span>{node.name}</span>
        {!isLeaf && node.children.size > 0 && (
          <span className="text-[10px] text-muted-foreground">({node.children.size})</span>
        )}
        <DifficultyStars d={node.difficulty} />
      </div>
      {open && hasChildren && (
        <div>
          {[...node.children.values()].map((c) => (
            <OutlineNodeView key={c.name} node={c} depth={depth + 1} onPick={onPick} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 单个知识点卡片
// ---------------------------------------------------------------------------
function KpCard({
  kp,
  isMath,
  onGoToKp,
}: {
  kp: KnowledgePointSummary;
  isMath: boolean;
  onGoToKp: (kid: string) => void;
}) {
  const { t } = useTranslation();
  const [showExamples, setShowExamples] = useState(false);
  const [jumping, setJumping] = useState<string | null>(null);
  const examples = kp.examples || [];

  const jump = async (kid: string) => {
    setJumping(kid);
    await onGoToKp(kid);
    setJumping(null);
  };

  return (
    <div id={`kp-${kp.id}`} className="p-3 rounded-lg border bg-card scroll-mt-4" data-testid={`kp-card-${kp.id}`}>
      {/* 头部 */}
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <Lightbulb className="w-4 h-4 text-amber-500 shrink-0" />
        <span className="font-medium text-sm">{kp.name}</span>
        <DifficultyStars d={kp.difficulty} />
        <span className="text-xs text-muted-foreground">{t(SUBJECT_DISPLAY[kp.subject] || kp.subject)}</span>
        {kp.grade && (
          <span className="text-[10px] px-1 py-0.5 rounded bg-muted text-muted-foreground">{kp.grade}</span>
        )}
        {kp.path && (
          <span className="text-[10px] text-muted-foreground ml-auto">{kp.path}</span>
        )}
      </div>

      {/* 总结 */}
      {kp.description && <p className="text-sm text-muted-foreground ml-6 mt-1">{kp.description}</p>}

      {/* 讲解 */}
      {kp.explanation && (
        <div className="ml-6 mt-2 rounded bg-muted/30 p-3">
          <MarkdownRenderer content={kp.explanation} variant="prose" />
        </div>
      )}

      {/* 公式与推导（数学） */}
      {isMath && kp.formula?.latex && (
        <div className="ml-6 mt-2">
          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
            <FlaskConical className="w-3 h-3" /> {t("Formula: {{name}}", { name: kp.formula.name || kp.name })}
          </div>
          <div className="px-3 py-2 rounded bg-muted/40 overflow-x-auto">
            <MarkdownRenderer content={`$$${kp.formula.latex}$$`} variant="prose" />
          </div>
          {kp.formula.derivation && (
            <div className="mt-2 rounded bg-muted/40 p-3">
              <div className="text-xs font-medium text-muted-foreground mb-1">{t("Derivation process")}</div>
              <MarkdownRenderer content={kp.formula.derivation} variant="prose" />
            </div>
          )}
        </div>
      )}

      {/* 可拖拽图形（数学图形化） */}
      {isMath && kp.figure?.type && (
        <div className="ml-6 mt-2">
          <div className="text-xs text-muted-foreground mb-1">✋ {t("Draggable demo")}</div>
          <MathWidget figure={kp.figure} />
        </div>
      )}

      {/* 实例（可折叠） */}
      {examples.length > 0 && (
        <div className="ml-6 mt-2">
          <button
            onClick={() => setShowExamples((v) => !v)}
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            {showExamples ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {t("Examples ({{count}})", { count: examples.length })}
          </button>
          {showExamples && (
            <div className="mt-2 space-y-2">
              {examples.map((ex, i) => (
                <div key={i} className="rounded border p-2">
                  {ex.title && <div className="text-xs font-medium mb-1">{ex.title}</div>}
                  <div className="text-sm">
                    <MarkdownRenderer content={ex.content} variant="prose" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 相关知识点 */}
      {(kp.related || []).length > 0 && (
        <div className="ml-6 mt-2 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">{t("Related:")}</span>
          {(kp.related || []).map((r) => (
            <button
              key={r.kp_id}
              onClick={() => jump(r.kp_id)}
              disabled={jumping === r.kp_id}
              className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border text-primary hover:bg-primary/10 disabled:opacity-60"
            >
              {jumping === r.kp_id && <Loader2 className="w-3 h-3 animate-spin" />}
              {r.name || r.kp_id}
              <span className="text-muted-foreground">·{r.relation}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
