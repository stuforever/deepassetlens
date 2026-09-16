/**
 * BookProgressTimeline —— 书籍生成进度时间线（mini 浮标 / compact 单行 / full 完整三态）。
 * 1:1 复刻自原仓 DeepTutor web/app/(workspace)/book/components/BookProgressTimeline.tsx（432 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/book-progress"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json；
 *    stage label/description 与动态 progress message 经本地 TR 字典直出，未命中回退原文，插值用本地 fmt()）；
 *  - lucide-react → @ant-design/icons 语义就近（Loader2→LoadingOutlined spin、Check→CheckOutlined、
 *    AlertTriangle→WarningOutlined、Lightbulb→BulbOutlined、Search→SearchOutlined、Network→ApartmentOutlined、
 *    ScanSearch→FileSearchOutlined、BookMarked→BookOutlined、LayoutList→OrderedListOutlined）；
 *  - import 契约：@/lib/book-progress → './book-progress'（并行 Agent 同步产出，导出名
 *    progressHasRunning / BookProgress / StageId / StageView 与原仓一致）；
 *  - Tailwind → antd 组件 + 最小内联样式（STATE_TONE 四态色彩逐项落成具体色值：
 *    pending=muted #f4f4f5/40、running=sky #38bdf8 系、completed=emerald #10b981 系、error=rose #f43f5e 系）；
 *  - 连续渐变进度条 → antd Progress（showInfo=false，渐变 strokeColor，等价 h-1.5→6px）；
 *  - animate-ping（mini 运行态圆点）→ 本地 <style> keyframes dsh-bpt-ping。
 * 不变：props 契约（progress/compact/mini/className）、stageProgressFraction、formatProgressMessage /
 *       formatStageDetail 的全部正则与单复数分支、collectCounters 计数器、activeStage 选取逻辑。
 */
import type { ComponentType, CSSProperties } from "react";
import { Progress } from "antd";
import {
  ApartmentOutlined,
  BookOutlined,
  BulbOutlined,
  CheckOutlined,
  FileSearchOutlined,
  LoadingOutlined,
  OrderedListOutlined,
  SearchOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  progressHasRunning,
  type BookProgress,
  type StageId,
  type StageView,
} from "./book-progress";

type Translate = (key: string, options?: Record<string, unknown>) => string;

export interface BookProgressTimelineProps {
  progress: BookProgress;
  /** Compact mode — single-line horizontal pill strip (for reader header). */
  compact?: boolean;
  /** Mini mode — extra-thin floating chip (line + circles) for top-right. */
  mini?: boolean;
  className?: string;
}

/** 直出中文模板渲染（替代 i18next 插值）：{{var}} → 值 */
function fmt(tpl: string, vars?: Record<string, string | number>): string {
  if (!vars) return tpl;
  return tpl.replace(/\{\{(\w+)\}\}/g, (m, k: string) =>
    Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m,
  );
}

/** 原仓 zh/app.json 译文直出表（stage 标签/描述、进度消息、计数器、状态名） */
const TR: Record<string, string> = {
  // 阶段标签（book-progress STAGE_LABELS）
  Ideation: "构思",
  "Source sweep": "资料扫描",
  Synthesis: "综合",
  Critique: "自检",
  "Overview chapter": "导览章节",
  Compilation: "编译",
  // 阶段描述
  "Drafting the proposal from your inputs.": "根据你的输入起草方案。",
  "Parallel multi-query retrieval across your KBs.":
    "在知识库中并行执行多查询检索。",
  "Spine + concept graph (draft → revise).": "章节主线与概念图（草稿 → 修订）。",
  "Self-review rounds tightening the spine.": "通过自检轮次优化章节主线。",
  "Auto-built table of contents + concept map.": "自动构建目录与概念图。",
  "Per-page block planning + generation.": "逐页规划并生成内容块。",
  // 阶段状态
  pending: "待处理",
  running: "运行中",
  completed: "已完成",
  error: "错误",
  // 实时消息
  "Proposal ready": "方案已就绪",
  "Book compilation complete": "书籍编译完成",
  "Book generation failed": "书籍生成失败",
  "Generating book": "正在生成书籍",
  "Source sweep done — {{queries}} queries, {{chunks}} chunks":
    "资料扫描完成：{{queries}} 次查询，{{chunks}} 个片段",
  "Spine ready — {{chapters}} chapters · {{concepts}} concepts":
    "章节主线就绪：{{chapters}} 章 · {{concepts}} 个概念",
  // 阶段详情
  "{{queries}} queries · {{chunks}} chunks": "{{queries}} 次查询 · {{chunks}} 个片段",
  "{{rounds}} round · {{issues}} issue": "{{rounds}} 轮 · {{issues}} 个问题",
  "{{rounds}} round · {{issues}} issues": "{{rounds}} 轮 · {{issues}} 个问题",
  "{{rounds}} rounds · {{issues}} issue": "{{rounds}} 轮 · {{issues}} 个问题",
  "{{rounds}} rounds · {{issues}} issues": "{{rounds}} 轮 · {{issues}} 个问题",
  "{{rounds}} round · {{chapters}} chapter": "{{rounds}} 轮 · {{chapters}} 章",
  "{{rounds}} round · {{chapters}} chapters": "{{rounds}} 轮 · {{chapters}} 章",
  "{{rounds}} rounds · {{chapters}} chapter": "{{rounds}} 轮 · {{chapters}} 章",
  "{{rounds}} rounds · {{chapters}} chapters": "{{rounds}} 轮 · {{chapters}} 章",
  "{{chapters}} chapters · {{concepts}} concepts":
    "{{chapters}} 章 · {{concepts}} 个概念",
  "{{pages}} page · {{blocks}} blocks": "{{pages}} 页 · {{blocks}} 个内容块",
  "{{pages}} pages · {{blocks}} blocks": "{{pages}} 页 · {{blocks}} 个内容块",
  // 计数器
  queries: "次查询",
  chunks: "个片段",
  chapters: "章",
  concepts: "个概念",
  "blocks ready": "个内容块就绪",
  "pages ready": "页已就绪",
  "block errors": "个内容块错误",
};

/** 直出 t()：命中字典取译文，否则回退原文（与 i18next 缺 key 行为一致） */
const tr: Translate = (key, options) =>
  TR[key] ? fmt(TR[key], options as Record<string, string | number>) : fmt(key, options as Record<string, string | number>);

const STAGE_ICONS: Record<
  StageId,
  ComponentType<{ style?: CSSProperties }>
> = {
  ideation: BulbOutlined,
  exploration: SearchOutlined,
  synthesis: ApartmentOutlined,
  critique: FileSearchOutlined,
  overview: BookOutlined,
  compilation: OrderedListOutlined,
};

// State → 具体色值（原 Tailwind tokens：muted / sky / emerald / rose 语义逐一保留）
const STATE_TONE = {
  pending: {
    fg: "#6b7280",
    bg: "rgba(244,244,245,0.4)",
    ring: "#e4e4e7",
    bar: "#e4e4e7",
  },
  running: {
    fg: "#0369a1",
    bg: "linear-gradient(135deg, rgba(56,189,248,0.2) 0%, rgba(129,140,248,0.15) 100%)",
    ring: "rgba(56,189,248,0.6)",
    bar: "linear-gradient(90deg, #38bdf8, #818cf8)",
  },
  completed: {
    fg: "#047857",
    bg: "rgba(16,185,129,0.1)",
    ring: "rgba(52,211,153,0.5)",
    bar: "linear-gradient(90deg, #34d399, #2dd4bf)",
  },
  error: {
    fg: "#be123c",
    bg: "rgba(244,63,94,0.1)",
    ring: "rgba(251,113,133,0.6)",
    bar: "#fb7185",
  },
} as const;

function stageProgressFraction(progress: BookProgress): number {
  const { ordered, stages } = progress;
  let value = 0;
  for (const id of ordered) {
    const s = stages[id].state;
    if (s === "completed") value += 1;
    else if (s === "running") value += 0.5;
    else if (s === "error") value += 1;
  }
  return Math.min(1, value / ordered.length);
}

const ICON_SIZE = 14; // h-3.5 w-3.5 → 14

function StageIcon({ id, state }: { id: StageId; state: StageView["state"] }) {
  if (state === "running")
    return <LoadingOutlined spin style={{ fontSize: ICON_SIZE }} />;
  if (state === "completed")
    return <CheckOutlined style={{ fontSize: ICON_SIZE }} />;
  if (state === "error")
    return <WarningOutlined style={{ fontSize: ICON_SIZE }} />;
  const Icon = STAGE_ICONS[id];
  return <Icon style={{ fontSize: ICON_SIZE }} />;
}

function formatProgressMessage(message: string): string {
  if (!message) return "";
  const sourceSweep = message.match(
    /^Source sweep done — (\d+) queries, (\d+) chunks$/,
  );
  if (sourceSweep) {
    return tr("Source sweep done — {{queries}} queries, {{chunks}} chunks", {
      queries: Number(sourceSweep[1]),
      chunks: Number(sourceSweep[2]),
    });
  }
  const spineReady = message.match(
    /^Spine ready — (\d+) chapters · (\d+) concepts$/,
  );
  if (spineReady) {
    return tr("Spine ready — {{chapters}} chapters · {{concepts}} concepts", {
      chapters: Number(spineReady[1]),
      concepts: Number(spineReady[2]),
    });
  }
  return tr(message);
}

function formatStageDetail(detail: string | undefined): string {
  if (!detail) return "";
  const sourceSweep = detail.match(/^(\d+) queries · (\d+) chunks$/);
  if (sourceSweep) {
    return tr("{{queries}} queries · {{chunks}} chunks", {
      queries: Number(sourceSweep[1]),
      chunks: Number(sourceSweep[2]),
    });
  }
  const critique = detail.match(/^(\d+) rounds? · (\d+) issues?$/);
  if (critique) {
    const rounds = Number(critique[1]);
    const issues = Number(critique[2]);
    const key =
      rounds === 1
        ? issues === 1
          ? "{{rounds}} round · {{issues}} issue"
          : "{{rounds}} round · {{issues}} issues"
        : issues === 1
          ? "{{rounds}} rounds · {{issues}} issue"
          : "{{rounds}} rounds · {{issues}} issues";
    return tr(key, { rounds, issues });
  }
  const synthesis = detail.match(/^(\d+) rounds? · (\d+) chapters?$/);
  if (synthesis) {
    const rounds = Number(synthesis[1]);
    const chapters = Number(synthesis[2]);
    const key =
      rounds === 1
        ? chapters === 1
          ? "{{rounds}} round · {{chapters}} chapter"
          : "{{rounds}} round · {{chapters}} chapters"
        : chapters === 1
          ? "{{rounds}} rounds · {{chapters}} chapter"
          : "{{rounds}} rounds · {{chapters}} chapters";
    return tr(key, { rounds, chapters });
  }
  const spine = detail.match(/^(\d+) chapters · (\d+) concepts$/);
  if (spine) {
    return tr("{{chapters}} chapters · {{concepts}} concepts", {
      chapters: Number(spine[1]),
      concepts: Number(spine[2]),
    });
  }
  const compilation = detail.match(/^(\d+) pages? · (\d+) blocks$/);
  if (compilation) {
    const pages = Number(compilation[1]);
    const blocks = Number(compilation[2]);
    return tr(
      pages === 1
        ? "{{pages}} page · {{blocks}} blocks"
        : "{{pages}} pages · {{blocks}} blocks",
      { pages, blocks },
    );
  }
  return tr(detail);
}

export default function BookProgressTimeline({
  progress,
  compact = false,
  mini = false,
  className = "",
}: BookProgressTimelineProps) {
  const { ordered, stages, message } = progress;
  const fraction = stageProgressFraction(progress);
  const activeStage =
    ordered.find((id) => stages[id].state === "running") ||
    ordered.find((id) => stages[id].state === "error") ||
    [...ordered].reverse().find((id) => stages[id].state === "completed") ||
    ordered[0];
  const activeView = stages[activeStage];
  const hasRunningStage = progressHasRunning(progress);
  const hasError = ordered.some((id) => stages[id].state === "error");
  const counters = collectCounters(progress, tr);
  const liveMessage = formatProgressMessage(message);
  const activeDetail = formatStageDetail(activeView.detail);

  // ── Mini mode: thin floating chip (top-right) ───────────────────────
  if (mini) {
    const terminal = !hasRunningStage;
    const activeLabel = tr(activeView.label);
    const tooltip = `${activeLabel}${activeDetail ? ` · ${activeDetail}` : ""}${
      liveMessage && message !== activeView.label ? ` · ${liveMessage}` : ""
    }`;
    return (
      <div
        className={className}
        style={{
          pointerEvents: "auto",
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          borderRadius: 999,
          border: "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.9)",
          padding: "4px 10px",
          fontSize: 11,
          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          backdropFilter: "blur(4px)",
        }}
        title={tooltip}
        aria-label={tooltip}
      >
        {/* animate-ping keyframes（mini 运行态圆点） */}
        <style>{`@keyframes dsh-bpt-ping { 75%, 100% { transform: scale(2); opacity: 0; } }`}</style>
        <LoadingOutlined
          spin
          style={{
            fontSize: 12,
            color: "#6b7280",
            opacity: terminal ? 0 : 1,
          }}
        />
        {/* line + circles strip */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 4 }}>
          {/* connector line behind the dots */}
          <div
            style={{
              position: "absolute",
              left: 6,
              right: 6,
              top: "50%",
              zIndex: 0,
              height: 1,
              transform: "translateY(-50%)",
              background: "#e4e4e7",
              pointerEvents: "none",
            }}
          />
          {ordered.map((id) => {
            const s = stages[id].state;
            const tone = STATE_TONE[s];
            return (
              <span
                key={id}
                title={`${tr(stages[id].label)} · ${tr(s)}`}
                style={{
                  position: "relative",
                  zIndex: 10,
                  display: "inline-flex",
                  height: 12,
                  width: 12,
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 999,
                  boxShadow: `0 0 0 1px ${tone.ring}`,
                  background: tone.bg,
                }}
              >
                {s === "running" && (
                  <span
                    style={{
                      position: "absolute",
                      inset: 0,
                      borderRadius: 999,
                      background: "rgba(56,189,248,0.4)",
                      animation:
                        "dsh-bpt-ping 1s cubic-bezier(0, 0, 0.2, 1) infinite",
                    }}
                  />
                )}
                {s === "completed" && (
                  <CheckOutlined style={{ fontSize: 8, color: "#059669" }} />
                )}
                {s === "error" && (
                  <WarningOutlined style={{ fontSize: 8, color: "#f43f5e" }} />
                )}
              </span>
            );
          })}
        </div>
        <span
          style={{
            maxWidth: 160,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            fontSize: 10.5,
            color: "#6b7280",
          }}
        >
          {activeLabel}
        </span>
        <span
          style={{
            fontVariantNumeric: "tabular-nums",
            fontSize: 10,
            fontWeight: 500,
            color: "#6b7280",
          }}
        >
          {Math.round(fraction * 100)}%
        </span>
      </div>
    );
  }

  if (compact) {
    return (
      <div
        className={className}
        style={{ display: "flex", alignItems: "center", gap: 12 }}
        title={liveMessage || tr(activeView.label)}
      >
        {/* Icon strip */}
        <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
          {ordered.map((id) => {
            const s = stages[id].state;
            const tone = STATE_TONE[s];
            return (
              <span
                key={id}
                title={`${tr(stages[id].label)} · ${tr(s)}`}
                style={{
                  display: "inline-flex",
                  height: 20,
                  width: 20,
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 999,
                  background: tone.bg,
                  color: tone.fg,
                }}
              >
                <StageIcon id={id} state={s} />
              </span>
            );
          })}
        </div>

        {/* Live caption */}
        <div
          style={{
            minWidth: 0,
            flex: 1,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            fontSize: 11,
            color: "#6b7280",
          }}
        >
          <span style={{ fontWeight: 500, color: "rgba(0,0,0,0.88)" }}>
            {tr(activeView.label)}
          </span>
          {activeDetail && (
            <span style={{ marginLeft: 6, opacity: 0.7 }}>· {activeDetail}</span>
          )}
          {liveMessage && message !== activeView.label && (
            <span style={{ marginLeft: 6, opacity: 0.7 }}>· {liveMessage}</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={className}
      style={{
        overflow: "hidden",
        borderRadius: 16,
        border: "1px solid #e4e4e7",
        background:
          "linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.6) 100%)",
        boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
      }}
    >
      {/* ── Top hero row: animated progress bar + live caption ───────── */}
      <div style={{ padding: "14px 16px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "#6b7280",
              }}
            >
              <LoadingOutlined
                spin
                style={{
                  fontSize: 12,
                  opacity: hasRunningStage ? 1 : 0,
                }}
              />
              {hasError && !hasRunningStage
                ? tr("Book generation failed")
                : tr("Generating book")}
            </div>
            <div
              style={{
                marginTop: 2,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                fontSize: 14,
                fontWeight: 500,
                color: "rgba(0,0,0,0.88)",
              }}
            >
              {tr(activeView.label)}
              {activeDetail && (
                <span
                  style={{
                    marginLeft: 6,
                    fontSize: 12,
                    fontWeight: 400,
                    color: "#6b7280",
                  }}
                >
                  · {activeDetail}
                </span>
              )}
            </div>
            {liveMessage && message !== activeView.label && (
              <div
                style={{
                  marginTop: 2,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                {liveMessage}
              </div>
            )}
          </div>
          <div
            style={{
              textAlign: "right",
              fontSize: 11,
              fontWeight: 500,
              color: "#6b7280",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {Math.round(fraction * 100)}%
          </div>
        </div>

        {/* Continuous gradient progress bar */}
        <Progress
          percent={Math.max(2, fraction * 100)}
          showInfo={false}
          strokeColor={{ "0%": "#38bdf8", "50%": "#818cf8", "100%": "#34d399" }}
          trailColor="rgba(244,244,245,0.6)"
          size={6}
          style={{ marginTop: 12 }}
        />
      </div>

      {/* ── Segmented stage strip ──────────────────────────────────── */}
      <div style={{ padding: 12 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
            gap: 6,
          }}
        >
          {ordered.map((id) => {
            const stage = stages[id];
            const tone = STATE_TONE[stage.state];
            const isActive = stage.state === "running";
            return (
              <div
                key={id}
                title={`${tr(stage.label)} — ${tr(stage.description)}`}
                style={{
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 8,
                  padding: 6,
                  boxShadow: `0 0 0 1px ${tone.ring}`,
                  background: tone.bg,
                  opacity: isActive ? 1 : 0.9,
                  transition: "all 0.2s",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    height: 20,
                    width: 20,
                    flexShrink: 0,
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 999,
                    background: tone.bg,
                    color: tone.fg,
                  }}
                >
                  <StageIcon id={id} state={stage.state} />
                </span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      fontSize: 11,
                      fontWeight: 500,
                      color: tone.fg,
                    }}
                  >
                    {tr(stage.label)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {counters.length > 0 && (
          <div
            style={{
              marginTop: 12,
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              columnGap: 12,
              rowGap: 4,
              borderTop: "1px solid #e4e4e7",
              paddingTop: 10,
              fontSize: 11,
            }}
          >
            {counters.map((item) => (
              <div
                key={item.label}
                style={{
                  display: "inline-flex",
                  alignItems: "baseline",
                  gap: 4,
                  color: "#6b7280",
                }}
              >
                <span
                  style={{
                    fontWeight: 600,
                    fontVariantNumeric: "tabular-nums",
                    color: "rgba(0,0,0,0.88)",
                  }}
                >
                  {item.value}
                </span>
                <span style={{ opacity: 0.8 }}>{item.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function collectCounters(
  progress: BookProgress,
  t: Translate,
): { label: string; value: string | number }[] {
  const items: { label: string; value: string | number }[] = [];
  if (progress.exploration.queryCount > 0) {
    items.push({ label: t("queries"), value: progress.exploration.queryCount });
  }
  if (progress.exploration.chunkCount > 0) {
    items.push({ label: t("chunks"), value: progress.exploration.chunkCount });
  }
  if (progress.synthesis.chapterCount > 0) {
    items.push({
      label: t("chapters"),
      value: progress.synthesis.chapterCount,
    });
  }
  if (progress.synthesis.conceptNodes > 0) {
    items.push({
      label: t("concepts"),
      value: `${progress.synthesis.conceptNodes}/${progress.synthesis.conceptEdges}`,
    });
  }
  if (progress.compilation.blocksReady > 0) {
    items.push({
      label: t("blocks ready"),
      value: progress.compilation.blocksReady,
    });
  }
  if (progress.compilation.pagesReady > 0) {
    items.push({
      label: t("pages ready"),
      value: progress.compilation.pagesReady,
    });
  }
  if (progress.compilation.blocksError > 0) {
    items.push({
      label: t("block errors"),
      value: progress.compilation.blocksError,
    });
  }
  return items;
}
