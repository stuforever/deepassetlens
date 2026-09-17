/**
 * ── 复刻来源与替换点（tupu antd 复刻，批9 F2 / SA-D）────────────────────────
 * 源文件：DeepTutor web/app/h5/atlas/page.tsx
 * 目标：frontend/src/pages/tutor/h5/H5Atlas.tsx（1:1 复刻，逻辑逐字保留）
 * 路由：/h5/atlas → /e/tutor-h5/atlas
 * 替换点：
 * - "use client" 删除；next/link → react-router Link；useSearchParams → react-router；
 * - lucide（Loader2/ChevronDown/BookOpen/MessageCircle/Map/Sparkles）→ @ant-design/icons
 *   （LoadingOutlined/DownOutlined/ReadOutlined/MessageOutlined/GlobalOutlined/StarOutlined）；
 * - "@/lib/self-learning-api" → "./h5shared/selfLearningApi"；fetch(apiUrl('/api/v1/...'))
 *   → fetch('/api/v1/...')（apiUrl pass-through 脱壳）；"@/lib/h5-utils" → "./h5shared/h5Utils"；
 * - "../components/H5Shell"、"@/components/h5/H5PageHeader"、"@/components/h5/H5Sheet" →
 *   "./h5shared/*"；站内链接前缀 /h5/* → /e/tutor-h5/*；
 * - Tailwind → 内联样式逐项对位。
 * 图件选型说明：原仓 H5 知识地图本身就是「缩进列表降级版」（源码注释：U8 第六篇正名，
 * 移动端不叫图谱，无 cytoscape），故无需平台图件/KpRelationGraph 降级，1:1 复刻
 * 分层缩进列表 + 着色圆点，节点/点击/详情抽屉交互语义原样保留。
 * ─────────────────────────────────────────────────────────────────────
 */
import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  LoadingOutlined,
  DownOutlined,
  ReadOutlined,
  MessageOutlined,
  GlobalOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { fetchLearnerProfile, type KpMasteryDto } from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";
import { H5PageHeader } from "./h5shared/H5PageHeader";
import { H5Sheet } from "./h5shared/H5Sheet";

/**
 * H5 知识地图（U8 第六篇正名：实际为缩进列表降级版，不叫"图谱"避免预期落差）：
 * kp_tree + learner-profile 掌握度着色。
 * 移动端降级为分层缩进列表 + 着色圆点（捏合缩放图性能不足时）。
 * 节点着色：mastered 绿 / learning 蓝 / weak 红 / new 灰。
 */

const SUBJECTS = [
  { key: "math", label: "数学" },
  { key: "chinese", label: "语文" },
  { key: "english", label: "英语" },
];

interface KpNode {
  id: string;
  name: string;
  subject: string;
  grade: string | null;
  difficulty: number;
  children: KpNode[];
  [k: string]: unknown;
}

function kpStatus(kp: KpMasteryDto | undefined): "mastered" | "learning" | "weak" | "new" {
  if (!kp) return "new";
  return kp.status;
}

const STATUS_DOT: Record<string, string> = {
  mastered: "#10b981",
  learning: "#3b82f6",
  weak: "#f43f5e",
  new: "#cbd5e1",
};
const STATUS_LABEL: Record<string, string> = {
  mastered: "已掌握",
  learning: "学习中",
  weak: "薄弱",
  new: "未学",
};

function H5AtlasContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const [subject, setSubject] = useState("math");
  const [tree, setTree] = useState<KpNode[]>([]);
  const [profile, setProfile] = useState<Record<string, KpMasteryDto>>({});
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<{ node: KpNode; kp?: KpMasteryDto } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [treeRes, prof] = await Promise.all([
        fetch(`/api/v1/curriculum/knowledge-points/tree?subject=${encodeURIComponent(subject)}`).then(
          (r) => (r.ok ? r.json() : { tree: [] }),
        ),
        fetchLearnerProfile(u || undefined),
      ]);
      setTree(treeRes.tree || []);
      setProfile(prof?.kp_mastery || {});
    } catch {
      setTree([]);
    } finally {
      setLoading(false);
    }
  }, [subject, u]);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = Object.values(profile).reduce(
    (acc, k) => {
      acc[k.status] = (acc[k.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  const renderNode = (node: KpNode, depth: number): React.ReactNode => {
    const kp = profile[node.id];
    const status = kpStatus(kp);
    const hasKids = (node.children || []).length > 0;
    return (
      <div key={node.id}>
        <button
          onClick={() => setSelected({ node, kp })}
          style={{
            width: "100%", textAlign: "left", display: "flex", alignItems: "center", gap: 8,
            padding: "8px 8px", borderRadius: 12, border: "none", cursor: "pointer", background: depth === 0 ? "rgba(238,242,255,0.5)" : "transparent",
            paddingLeft: `${depth * 18 + 8}px`,
            boxSizing: "border-box",
          }}
        >
          <span style={{ width: 10, height: 10, borderRadius: 999, flexShrink: 0, background: STATUS_DOT[status] }} />
          <span
            style={{
              flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              fontWeight: hasKids ? 600 : 400, color: hasKids ? "#1e293b" : "#334155",
            }}
          >
            {node.name}
          </span>
          {kp && (
            <span style={{ fontSize: 11, color: "#94a3b8", flexShrink: 0 }}>
              {Math.round(kp.mastery * 100)}%
            </span>
          )}
          {hasKids && <DownOutlined style={{ fontSize: 14, color: "#cbd5e1", flexShrink: 0 }} />}
        </button>
        {(node.children || []).map((c) => renderNode(c, depth + 1))}
      </div>
    );
  };

  return (
    <H5Shell active="home" onRefresh={load}>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(90deg, #14b8a6, #059669)", color: "#fff", padding: "40px 20px 56px", borderRadius: "0 0 24px 24px" }}>
        <H5PageHeader title={<span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><GlobalOutlined style={{ fontSize: 20 }} /> 知识地图</span>} />
        <div style={{ marginTop: 4, color: "#ccfbf1", fontSize: 12 }}>按章节浏览知识点掌握度 · 点击看详情</div>
      </div>

      <div style={{ padding: "0 16px 40px", marginTop: -32 }}>
        {/* 学科切换 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0", padding: 8, display: "flex", gap: 4 }}>
          {SUBJECTS.map((s) => (
            <button
              key={s.key}
              onClick={() => setSubject(s.key)}
              style={{
                flex: 1, padding: "8px 0", borderRadius: 12, fontSize: 14, fontWeight: 500,
                transition: "all .15s", cursor: "pointer", border: "none",
                background: subject === s.key ? "#0d9488" : "transparent",
                color: subject === s.key ? "#fff" : "#64748b",
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* 掌握度统计 */}
        <div style={{ marginTop: 12, background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0", padding: 12, display: "flex", justifyContent: "space-around", textAlign: "center" }}>
          {(["mastered", "learning", "weak", "new"] as const).map((s) => (
            <div key={s}>
              <div style={{ margin: "0 auto", width: 10, height: 10, borderRadius: 999, background: STATUS_DOT[s] }} />
              <div style={{ fontSize: 18, fontWeight: 700, color: "#334155", marginTop: 4 }}>{counts[s] || 0}</div>
              <div style={{ fontSize: 10, color: "#94a3b8" }}>{STATUS_LABEL[s]}</div>
            </div>
          ))}
        </div>

        {/* 图谱主体 */}
        <div style={{ marginTop: 16, background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0", padding: 12 }}>
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
              <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载图谱…
            </div>
          ) : tree.length === 0 ? (
            <div style={{ textAlign: "center", padding: "56px 0", color: "#94a3b8" }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>🗺️</div>
              暂无知识点数据
            </div>
          ) : (
            <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
              {tree.map((n) => renderNode(n, 0))}
            </div>
          )}
        </div>

        <div style={{ marginTop: 12, fontSize: 12, color: "#94a3b8", padding: "0 4px", textAlign: "center" }}>
          绿=已掌握 · 蓝=学习中 · 红=薄弱 · 灰=未学
        </div>
      </div>

      {/* 知识点微卡抽屉（S1/M23：H5Sheet 统一基座，长内容可滚） */}
      <H5Sheet open={!!selected} onClose={() => setSelected(null)} title={
        selected ? (
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 12, height: 12, borderRadius: 999, display: "inline-block", background: STATUS_DOT[kpStatus(selected.kp)] }} />
            {selected.node.name}
          </span>
        ) : null
      }>
        {selected && (
          <>
            <div style={{ padding: "0 20px 8px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, textAlign: "center", marginBottom: 16 }}>
                <div style={{ background: "#f8fafc", borderRadius: 12, padding: "8px 0" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#334155" }}>
                    {selected.kp ? Math.round(selected.kp.mastery * 100) : 0}%
                  </div>
                  <div style={{ fontSize: 10, color: "#94a3b8" }}>掌握度</div>
                </div>
                <div style={{ background: "#f8fafc", borderRadius: 12, padding: "8px 0" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#334155" }}>
                    {selected.node.difficulty || "—"}
                  </div>
                  <div style={{ fontSize: 10, color: "#94a3b8" }}>难度</div>
                </div>
                <div style={{ background: "#f8fafc", borderRadius: 12, padding: "8px 0" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#334155" }}>
                    {STATUS_LABEL[kpStatus(selected.kp)]}
                  </div>
                  <div style={{ fontSize: 10, color: "#94a3b8" }}>状态</div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
                <a
                  href={withU(`/e/tutor-h5/learn`, u)}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "12px 0", borderRadius: 16, background: "#4f46e5", color: "#fff", fontSize: 14, fontWeight: 500, textDecoration: "none" }}
                >
                  <ReadOutlined style={{ fontSize: 16 }} /> 看讲解
                </a>
                <Link
                  to={withU("/e/tutor-h5/chat", u)}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "12px 0", borderRadius: 16, background: "#7c3aed", color: "#fff", fontSize: 14, fontWeight: 500, textDecoration: "none" }}
                >
                  <MessageOutlined style={{ fontSize: 16 }} /> 找 AI 补
                </Link>
              </div>
              {selected.kp && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#94a3b8", display: "flex", alignItems: "flex-start", gap: 4 }}>
                  <StarOutlined style={{ fontSize: 14, marginTop: 2, flexShrink: 0 }} />
                  {selected.kp.attempts > 0
                    ? `已练习 ${selected.kp.attempts} 次，正确率 ${Math.round((selected.kp.correct_rate || 0) * 100)}%`
                    : "尚未练习，去学一章或做道题开始积累掌握度"}
                </div>
              )}
            </div>
          </>
        )}
      </H5Sheet>
    </H5Shell>
  );
}

export default function H5AtlasPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载中…
        </div>
      }
    >
      <H5AtlasContent />
    </Suspense>
  );
}
