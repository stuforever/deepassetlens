/**
 * 复刻自 DeepTutor 原仓 web/components/h5/ChatPlusPanel.tsx（整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. next/link Link → react-router-dom Link；/h5/learn → /e/tutor/h5/learn（withU 原样）；
 * 3. lucide 图标：原文件 import 的 BrainCircuit/Clapperboard/GraduationCap/
 *    MessageSquare/Microscope/PenLine/BarChart3/X 在 JSX 中未使用（UI 全用 emoji），
 *    移植后按 tupu tsconfig noUnusedLocals 纪律删除未用导入；实际使用的
 *    ChevronRight→RightOutlined、Check→CheckOutlined、Loader2→LoadingOutlined、
 *    FileText→FileTextOutlined；
 * 4. @/lib/* → ./personasApi、./llmOptions、./toolsSettings、./playgroundConfig、
 *    ./quizTypes、./researchTypes、./appShellStorage；unified-ws/book-api/
 *    knowledge-api/notebook-api/book-references/visualize-types → 批8 admin/*；
 *    withU → ./h5Utils；H5Sheet → ./H5Sheet（同目录已有）；
 * 5. Tailwind → 内联样式 + 组件级 <style> 承接 active: 伪类（Tailwind 调色板 hex 直用）；
 *    data-testid 全量保留。
 *
 * 第十一篇 N5：对话「＋」动作面板——桌面 ChatComposer 能力面的移动版 1:1。
 *
 * 复用桌面同源 lib/API（零新增后端）：
 * - 能力模式：桌面 CAPABILITIES 7 项清单 + quiz-types/visualize-types/research-types 的
 *   build*WSConfig + playground-config 持久化；
 * - 人格 listPersonas / 模型 listLLMOptions / 工具 getEnabledOptionalTools /
 *   知识库 listKnowledgeBases / 笔记本 listNotebooks+getNotebook /
 *   书引用 bookApi.list+get（selectedBooksToPayload 语义）/ 语言 writeStoredLanguage。
 * 只写移动 UI（底部二级弹层）。
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { H5Sheet } from "./H5Sheet";
import {
  RightOutlined,
  CheckOutlined,
  LoadingOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { withU } from "./h5Utils";
import { listPersonas } from "./personasApi";
import { listLLMOptions, sameLLMSelection } from "./llmOptions";
import type { LLMSelection } from "../../admin/unified-ws";
import { getEnabledOptionalTools } from "./toolsSettings";
import { listKnowledgeBases } from "../../admin/knowledge-api";
import { listNotebooks, getNotebook } from "../../admin/notebook-api";
import { bookApi } from "../../admin/book-api";
import {
  selectedBooksToPayload,
  type SelectedBookReference,
} from "../../admin/book-references";
import {
  loadCapabilityPlaygroundConfigs,
  saveCapabilityPlaygroundConfig,
  type CapabilityPlaygroundConfigMap,
} from "./playgroundConfig";
import {
  DEFAULT_QUIZ_CONFIG,
  buildQuizWSConfig,
  type DeepQuestionFormConfig,
} from "./quizTypes";
import {
  DEFAULT_VISUALIZE_CONFIG,
  buildVisualizeWSConfig,
  type VisualizeFormConfig,
} from "../../admin/visualize-types";
import {
  buildResearchWSConfig,
  type DeepResearchFormConfig,
} from "./researchTypes";
import { writeStoredLanguage, readStoredLanguage } from "./appShellStorage";

// Tailwind 调色板 hex 对位（本文件局部用）。
const V600 = "#7c3aed";
const V500 = "#8b5cf6";
const V400 = "#a78bfa";
const V50 = "#f5f3ff";
const S50 = "#f8fafc";
const S100 = "#f1f5f9";
const S200 = "#e2e8f0";
const S400 = "#94a3b8";
const S600 = "#475569";
const S700 = "#334155";
const S800 = "#1e293b";

const PlusPanelStyleBlock = () => (
  <style>{`
.cpp-row:active{background:${S50};}
.cpp-camera:active{background:#fee2e2;}
.cpp-album:active{background:#fef3c7;}
.cpp-doc:active{background:#e0f2fe;}
.cpp-optbtn:active{background:${S50};}
.cpp-toggle{transition:background-color .15s;}
.cpp-knob{transition:all .15s;}
  `}</style>
);

export type NotebookRefPayload = { notebook_id: string; record_ids: string[] };

/** 能力项（桌面 CAPABILITIES 的移动清单；loop 引擎项与桌面同语义） */
const CAPABILITIES: {
  value: string;
  label: string;
  emoji: string;
  desc: string;
  configurable?: boolean;
}[] = [
  { value: "", label: "自由对话", emoji: "💬", desc: "灵活对话，可用任意工具" },
  { value: "deep_solve", label: "深度解题", emoji: "🧮", desc: "多步推理与解题" },
  { value: "mastery_path", label: "精通辅导", emoji: "🏆", desc: "按精通之路带练（需先选路径）" },
  { value: "deep_question", label: "智能出题", emoji: "❓", desc: "自动出题并判分", configurable: true },
  { value: "deep_research", label: "深度研究", emoji: "🔍", desc: "多智能体综合研究", configurable: true },
  { value: "visualize", label: "图表可视化", emoji: "📊", desc: "图表/SVG/网页/动画", configurable: true },
  { value: "math_animator", label: "数学动画", emoji: "🎬", desc: "概念演示动画", configurable: true },
  { value: "wrong_intake", label: "录错题", emoji: "📝", desc: "对话多轮录入错题", configurable: true },
];

const CAP_LABEL: Record<string, string> = Object.fromEntries(
  CAPABILITIES.map((c) => [c.value, c.label]),
);

export function capabilityShortLabel(cap: string | null): string {
  if (!cap) return "自由对话";
  return CAP_LABEL[cap] || cap;
}

const QUIZ_TYPES: { value: string; label: string }[] = [
  { value: "choice", label: "选择题" },
  { value: "fill_in_blank", label: "填空题" },
  { value: "short_answer", label: "简答题" },
  { value: "concept", label: "概念题" },
];

type SubPanel =
  | null
  | "capability"
  | "persona"
  | "model"
  | "tools"
  | "kbs"
  | "notebook"
  | "book"
  | "language";

interface ChatPlusPanelProps {
  open: boolean;
  onClose: () => void;
  u: string;
  activeCapability: string | null;
  onSetCapability: (cap: string | null) => void;
  persona: string;
  onSetPersona: (p: string) => void;
  llmSelection: LLMSelection | null;
  onSetLLM: (sel: LLMSelection | null) => void;
  tools: string[];
  onSetTools: (t: string[]) => void;
  kbs: string[];
  onSetKBs: (k: string[]) => void;
  notebookRefs: NotebookRefPayload[];
  onSetNotebookRefs: (v: NotebookRefPayload[]) => void;
  bookRefs: SelectedBookReference[];
  onSetBookRefs: (v: SelectedBookReference[]) => void;
  /** 拍照/相册/文档：交由页面统一分类 + 预览 */
  onPickFiles: (files: File[]) => void;
  /** 能力配置确认后通知页面（页面发送时读取同一份 localStorage 配置） */
  capabilityConfigs: CapabilityPlaygroundConfigMap;
  onCapabilityConfigsChange: (next: CapabilityPlaygroundConfigMap) => void;
}

export default function ChatPlusPanel(props: ChatPlusPanelProps) {
  const { open, onClose, u } = props;
  const [sub, setSub] = useState<SubPanel>(null);

  useEffect(() => {
    if (!open) setSub(null);
  }, [open]);

  if (!open) return null;

  const closeAll = () => {
    setSub(null);
    onClose();
  };

  return (
    // S1（M23）：H5Sheet 统一基座；各 sub 面板自带 SheetHeader（返回/关闭），
    // 故外层不渲染 title。data-testid 保留（e2e 依赖 chat-plus-panel）。
    <H5Sheet open onClose={closeAll} testId="chat-plus-panel">
      <PlusPanelStyleBlock />
      <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
        {sub === null && (
          <MainMenu {...props} onOpen={setSub} onClose={closeAll} />
        )}
        {sub === "capability" && <CapabilityPanel {...props} onBack={() => setSub(null)} />}
        {sub === "persona" && <PersonaPanel {...props} onBack={() => setSub(null)} />}
        {sub === "model" && <ModelPanel {...props} onBack={() => setSub(null)} />}
        {sub === "tools" && <ToolsPanel {...props} onBack={() => setSub(null)} />}
        {sub === "kbs" && <KbPanel {...props} onBack={() => setSub(null)} />}
        {sub === "notebook" && <NotebookPanel {...props} onBack={() => setSub(null)} />}
        {sub === "book" && <BookPanel {...props} onBack={() => setSub(null)} u={u} />}
        {sub === "language" && <LanguagePanel {...props} onBack={() => setSub(null)} onClose={closeAll} />}
      </div>
    </H5Sheet>
  );
}

function SheetHeader({ title, onBack }: { title: string; onBack?: () => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      <h3 style={{ margin: 0, fontWeight: 600, fontSize: 14, display: "flex", alignItems: "center", gap: 6 }}>{title}</h3>
      {onBack ? (
        <button onClick={onBack} style={{ fontSize: 12, color: S400, border: "none", background: "transparent", cursor: "pointer" }}>
          返回 ↑
        </button>
      ) : (
        <button onClick={onBack} style={{ fontSize: 12, color: S400, border: "none", background: "transparent", cursor: "pointer" }}>
          关闭 ✕
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- 主菜单 //

function MainMenu({
  onOpen,
  onClose,
  onPickFiles,
}: ChatPlusPanelProps & { onOpen: (s: SubPanel) => void; onClose: () => void }) {
  const cameraRef = React.useRef<HTMLInputElement>(null);
  const albumRef = React.useRef<HTMLInputElement>(null);
  const docRef = React.useRef<HTMLInputElement>(null);

  const Row = ({
    emoji,
    label,
    hint,
    onClick,
    testid,
  }: {
    emoji: string;
    label: string;
    hint?: string;
    onClick: () => void;
    testid?: string;
  }) => (
    <button
      onClick={onClick}
      data-testid={testid}
      className="cpp-row"
      style={{
        width: "100%", display: "flex", alignItems: "center", gap: 12,
        padding: "12px 12px", borderRadius: 16, border: `1px solid ${S100}`,
        textAlign: "left", background: "transparent", cursor: "pointer",
      }}
    >
      <span style={{ fontSize: 20, width: 32, textAlign: "center", flexShrink: 0 }}>{emoji}</span>
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: "block", fontSize: 14, fontWeight: 500, color: S800 }}>{label}</span>
        {hint && (
          <span
            style={{
              display: "block", fontSize: 12, color: S400, marginTop: 2,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}
          >
            {hint}
          </span>
        )}
      </span>
      <RightOutlined style={{ fontSize: 14, color: "#cbd5e1", flexShrink: 0 }} />
    </button>
  );

  return (
    <>
      <SheetHeader title="＋ 添加 / 设置" />
      {/* 附件三入口（隐藏 input 直接拉起系统相机/相册/文件） */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginBottom: 12 }}>
        <button
          onClick={() => cameraRef.current?.click()}
          data-testid="plus-camera"
          className="cpp-camera"
          style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
            padding: "14px 0", borderRadius: 16, background: "#fef2f2",
            border: "1px solid #fee2e2", cursor: "pointer",
          }}
        >
          <span style={{ fontSize: 24 }}>📷</span>
          <span style={{ fontSize: 12, fontWeight: 500, color: "#e11d48" }}>拍照</span>
        </button>
        <button
          onClick={() => albumRef.current?.click()}
          data-testid="plus-album"
          className="cpp-album"
          style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
            padding: "14px 0", borderRadius: 16, background: "#fffbeb",
            border: "1px solid #fef3c7", cursor: "pointer",
          }}
        >
          <span style={{ fontSize: 24 }}>🖼️</span>
          <span style={{ fontSize: 12, fontWeight: 500, color: "#d97706" }}>相册</span>
        </button>
        <button
          onClick={() => docRef.current?.click()}
          data-testid="plus-doc"
          className="cpp-doc"
          style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
            padding: "14px 0", borderRadius: 16, background: "#f0f9ff",
            border: "1px solid #e0f2fe", cursor: "pointer",
          }}
        >
          <span style={{ fontSize: 24 }}>📄</span>
          <span style={{ fontSize: 12, fontWeight: 500, color: "#0284c7" }}>文档</span>
        </button>
      </div>
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={(e) => {
          if (e.target.files?.length) onPickFiles(Array.from(e.target.files));
          e.target.value = "";
          onClose();
        }}
      />
      <input
        ref={albumRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: "none" }}
        onChange={(e) => {
          if (e.target.files?.length) onPickFiles(Array.from(e.target.files));
          e.target.value = "";
          onClose();
        }}
      />
      <input
        ref={docRef}
        type="file"
        multiple
        accept="image/*,.pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.json"
        style={{ display: "none" }}
        onChange={(e) => {
          if (e.target.files?.length) onPickFiles(Array.from(e.target.files));
          e.target.value = "";
          onClose();
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <Row
          emoji="🧠"
          label="能力模式"
          testid="menu-capability"
          onClick={() => onOpen("capability")}
        />
        <Row emoji="🎭" label="人格" testid="menu-persona" onClick={() => onOpen("persona")} />
        <Row emoji="🤖" label="模型" testid="menu-model" onClick={() => onOpen("model")} />
        <Row emoji="🔧" label="工具开关" testid="menu-tools" onClick={() => onOpen("tools")} />
        <Row emoji="📚" label="知识库" testid="menu-kbs" onClick={() => onOpen("kbs")} />
        <Row
          emoji="📓"
          label="笔记本引用"
          testid="menu-notebook"
          onClick={() => onOpen("notebook")}
        />
        <Row emoji="📖" label="书引用" testid="menu-book" onClick={() => onOpen("book")} />
        <Row emoji="🌐" label="语言" testid="menu-language" onClick={() => onOpen("language")} />
      </div>
    </>
  );
}

// ------------------------------------------------------------- 能力模式 //

function CapabilityPanel({
  activeCapability,
  onSetCapability,
  capabilityConfigs,
  onCapabilityConfigsChange,
  u,
  onClose,
  onBack,
}: ChatPlusPanelProps & { onBack: () => void }) {
  const [configFor, setConfigFor] = useState<string | null>(null);
  // 简化配置草稿（复用桌面 playground-config 持久化）
  const [quizCfg, setQuizCfg] = useState<DeepQuestionFormConfig>({
    ...DEFAULT_QUIZ_CONFIG,
    ...(capabilityConfigs.deep_question?.config as Partial<DeepQuestionFormConfig>),
  });
  const [vizCfg, setVizCfg] = useState<VisualizeFormConfig>({
    ...DEFAULT_VISUALIZE_CONFIG,
    ...(capabilityConfigs.visualize?.config as Partial<VisualizeFormConfig>),
  });
  const [researchCfg, setResearchCfg] = useState<DeepResearchFormConfig>({
    mode: "",
    depth: "",
    ...((capabilityConfigs.deep_research?.config as Partial<DeepResearchFormConfig>) || {}),
  });

  const pick = (cap: string) => {
    const def = CAPABILITIES.find((c) => c.value === cap);
    if (cap === "mastery_path") {
      // 精通辅导必须挂路径：引导去选路（与顶栏「开始辅导」同语义）
      onSetCapability("mastery_path");
      onClose?.();
      return;
    }
    if (def?.configurable) {
      setConfigFor(cap);
      return;
    }
    onSetCapability(cap === "" ? null : cap);
    // 选定能力即收起面板（桌面 ChatComposer 同语义：选完回输入区）
    onClose?.();
  };

  const confirmConfig = (cap: string) => {
    let config: Record<string, unknown> = {};
    if (cap === "deep_question") config = buildQuizWSConfig(quizCfg);
    if (cap === "visualize") config = buildVisualizeWSConfig(vizCfg);
    if (cap === "deep_research") {
      if (!researchCfg.mode || !researchCfg.depth) {
        return; // 必填未选，按钮已禁用
      }
      config = buildResearchWSConfig(researchCfg);
    }
    if (cap === "wrong_intake") config = {}; // 无需额外配置，直接走对话流程
    const next = saveCapabilityPlaygroundConfig(capabilityConfigs, cap, {
      enabledTools: [],
      knowledgeBase: "",
      config,
    });
    onCapabilityConfigsChange(next);
    onSetCapability(cap);
    setConfigFor(null);
    // 确认即收起面板（回输入区直接发）
    onClose?.();
  };

  if (configFor === "deep_question") {
    return (
      <>
        <SheetHeader title="❓ 智能出题 · 设置" onBack={() => setConfigFor(null)} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="config-deep_question">
          <div>
            <div style={{ fontSize: 12, color: S400, marginBottom: 4 }}>题目数量</div>
            <div style={{ display: "flex", gap: 6 }}>
              {[3, 5, 8, 10].map((n) => (
                <button
                  key={n}
                  onClick={() => setQuizCfg({ ...quizCfg, num_questions: n })}
                  style={{
                    flex: 1, padding: "8px 0", borderRadius: 12, fontSize: 14,
                    border: `1px solid ${quizCfg.num_questions === n ? V600 : S200}`,
                    background: quizCfg.num_questions === n ? V600 : "#ffffff",
                    color: quizCfg.num_questions === n ? "#ffffff" : S600,
                    fontWeight: quizCfg.num_questions === n ? 500 : 400,
                    cursor: "pointer",
                  }}
                >
                  {n} 题
                </button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: S400, marginBottom: 4 }}>难度</div>
            <div style={{ display: "flex", gap: 6 }}>
              {[
                { v: "auto", l: "自动" },
                { v: "easy", l: "容易" },
                { v: "medium", l: "中等" },
                { v: "hard", l: "困难" },
              ].map((d) => (
                <button
                  key={d.v}
                  onClick={() => setQuizCfg({ ...quizCfg, difficulty: d.v })}
                  style={{
                    flex: 1, padding: "8px 0", borderRadius: 12, fontSize: 14,
                    border: `1px solid ${quizCfg.difficulty === d.v ? V600 : S200}`,
                    background: quizCfg.difficulty === d.v ? V600 : "#ffffff",
                    color: quizCfg.difficulty === d.v ? "#ffffff" : S600,
                    fontWeight: quizCfg.difficulty === d.v ? 500 : 400,
                    cursor: "pointer",
                  }}
                >
                  {d.l}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: S400, marginBottom: 4 }}>题型（不选 = 自动搭配）</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {QUIZ_TYPES.map((t) => {
                const on = quizCfg.question_types.includes(t.value as any);
                return (
                  <button
                    key={t.value}
                    onClick={() =>
                      setQuizCfg({
                        ...quizCfg,
                        question_types: on
                          ? quizCfg.question_types.filter((x) => x !== t.value)
                          : [...quizCfg.question_types, t.value as any],
                      })
                    }
                    style={{
                      padding: "6px 12px", borderRadius: 999, fontSize: 12,
                      border: `1px solid ${on ? V600 : S200}`,
                      background: on ? V600 : "#ffffff",
                      color: on ? "#ffffff" : S600,
                      cursor: "pointer",
                    }}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
          <button
            onClick={() => confirmConfig("deep_question")}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 16, background: V600,
              color: "#ffffff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer",
            }}
          >
            确认，开始出题
          </button>
        </div>
      </>
    );
  }

  if (configFor === "visualize") {
    return (
      <>
        <SheetHeader title="📊 图表可视化 · 设置" onBack={() => setConfigFor(null)} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="config-visualize">
          <div>
            <div style={{ fontSize: 12, color: S400, marginBottom: 4 }}>呈现方式</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 6 }}>
              {[
                { v: "auto", l: "自动" },
                { v: "chartjs", l: "图表" },
                { v: "svg", l: "SVG 图" },
                { v: "mermaid", l: "流程图" },
                { v: "html", l: "网页" },
                { v: "manim_video", l: "动画" },
              ].map((m) => (
                <button
                  key={m.v}
                  onClick={() => setVizCfg({ ...vizCfg, render_mode: m.v as any })}
                  style={{
                    padding: "8px 0", borderRadius: 12, fontSize: 12,
                    border: `1px solid ${vizCfg.render_mode === m.v ? "#0284c7" : S200}`,
                    background: vizCfg.render_mode === m.v ? "#0284c7" : "#ffffff",
                    color: vizCfg.render_mode === m.v ? "#ffffff" : S600,
                    fontWeight: vizCfg.render_mode === m.v ? 500 : 400,
                    cursor: "pointer",
                  }}
                >
                  {m.l}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() => confirmConfig("visualize")}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 16, background: "#0284c7",
              color: "#ffffff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer",
            }}
          >
            确认
          </button>
        </div>
      </>
    );
  }

  if (configFor === "deep_research") {
    const ready = !!researchCfg.mode && !!researchCfg.depth;
    return (
      <>
        <SheetHeader title="🔍 深度研究 · 设置" onBack={() => setConfigFor(null)} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="config-deep_research">
          <div>
            <div style={{ fontSize: 12, color: S400, marginBottom: 4 }}>产出形式</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 6 }}>
              {[
                { v: "notes", l: "学习笔记" },
                { v: "report", l: "研究报告" },
                { v: "comparison", l: "对比分析" },
                { v: "learning_path", l: "学习路径" },
              ].map((m) => (
                <button
                  key={m.v}
                  onClick={() => setResearchCfg({ ...researchCfg, mode: m.v as any })}
                  style={{
                    padding: "10px 0", borderRadius: 12, fontSize: 14,
                    border: `1px solid ${researchCfg.mode === m.v ? "#059669" : S200}`,
                    background: researchCfg.mode === m.v ? "#059669" : "#ffffff",
                    color: researchCfg.mode === m.v ? "#ffffff" : S600,
                    cursor: "pointer",
                  }}
                >
                  {m.l}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: S400, marginBottom: 4 }}>深度</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 6 }}>
              {[
                { v: "quick", l: "快速" },
                { v: "standard", l: "标准" },
                { v: "deep", l: "深入" },
              ].map((d) => (
                <button
                  key={d.v}
                  onClick={() => setResearchCfg({ ...researchCfg, depth: d.v as any })}
                  style={{
                    padding: "8px 0", borderRadius: 12, fontSize: 14,
                    border: `1px solid ${researchCfg.depth === d.v ? "#059669" : S200}`,
                    background: researchCfg.depth === d.v ? "#059669" : "#ffffff",
                    color: researchCfg.depth === d.v ? "#ffffff" : S600,
                    cursor: "pointer",
                  }}
                >
                  {d.l}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() => confirmConfig("deep_research")}
            disabled={!ready}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 16, background: "#059669",
              color: "#ffffff", fontSize: 14, fontWeight: 500, border: "none",
              cursor: "pointer", opacity: !ready ? 0.4 : 1,
            }}
          >
            {ready ? "确认" : "先选产出形式与深度"}
          </button>
        </div>
      </>
    );
  }

  if (configFor === "math_animator") {
    return (
      <>
        <SheetHeader title="🎬 数学动画 · 设置" onBack={() => setConfigFor(null)} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="config-math_animator">
          <div style={{ fontSize: 14, color: S600, background: S50, borderRadius: 16, padding: 12 }}>
            直接在输入框描述想演示的概念（如「演示圆柱侧面展开」），生成后可播放与重渲染。
          </div>
          <button
            onClick={() => confirmConfig("math_animator")}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 16, background: "#f43f5e",
              color: "#ffffff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer",
            }}
          >
            确认
          </button>
        </div>
      </>
    );
  }

  if (configFor === "wrong_intake") {
    return (
      <>
        <SheetHeader title="📝 录错题 · 设置" onBack={() => setConfigFor(null)} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="config-wrong_intake">
          <div style={{ fontSize: 14, color: S600, background: S50, borderRadius: 16, padding: 12 }}>
            直接口述错题即可，AI 会提取题干、正误答案并和你确认后存入错题本。
          </div>
          <button
            onClick={() => confirmConfig("wrong_intake")}
            data-testid="cap-wrong_intake-confirm"
            style={{
              width: "100%", padding: "12px 0", borderRadius: 16, background: V600,
              color: "#ffffff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer",
            }}
          >
            开始录题
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <SheetHeader title="🧠 能力模式" onBack={onBack} />
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="capability-list">
        {CAPABILITIES.map((c) => {
          const active = (activeCapability || "") === c.value;
          return (
            <button
              key={c.value || "chat"}
              onClick={() => pick(c.value)}
              data-testid={`cap-${c.value || "chat"}`}
              className={active ? "" : "cpp-row"}
              style={{
                width: "100%", display: "flex", alignItems: "center", gap: 12,
                padding: "12px 12px", borderRadius: 16, textAlign: "left",
                border: `1px solid ${active ? V400 : S100}`,
                background: active ? V50 : "transparent", cursor: "pointer",
              }}
            >
              <span style={{ fontSize: 20, width: 32, textAlign: "center", flexShrink: 0 }}>{c.emoji}</span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", fontSize: 14, fontWeight: 500, color: S800 }}>
                  {c.label}
                  {active && <span style={{ marginLeft: 8, fontSize: 11, color: V500 }}>当前</span>}
                </span>
                <span style={{ display: "block", fontSize: 12, color: S400, marginTop: 2 }}>{c.desc}</span>
              </span>
              {active && <CheckOutlined style={{ fontSize: 14, color: V500, flexShrink: 0 }} />}
            </button>
          );
        })}
      </div>
    </>
  );
}

// ----------------------------------------------------------------- 人格 //

function PersonaPanel({ persona, onSetPersona, onBack }: ChatPlusPanelProps & { onBack: () => void }) {
  const [list, setList] = useState<{ name: string; description: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    listPersonas()
      .then((ps) => alive && setList(ps))
      .catch((e) => alive && setErr(e?.message || "加载失败"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const pick = (name: string) => {
    onSetPersona(name);
    onBack();
  };

  return (
    <>
      <SheetHeader title="🎭 人格" onBack={onBack} />
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
          <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
        </div>
      ) : err ? (
        <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>{err}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="persona-list">
          <button
            onClick={() => pick("")}
            style={{
              width: "100%", textAlign: "left", padding: "12px 12px", borderRadius: 16,
              border: `1px solid ${!persona ? V400 : S100}`,
              background: !persona ? V50 : "transparent", cursor: "pointer",
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 500 }}>默认（无人格）</div>
          </button>
          {list.map((p) => (
            <button
              key={p.name}
              onClick={() => pick(p.name)}
              className={persona === p.name ? "" : "cpp-row"}
              style={{
                width: "100%", textAlign: "left", padding: "12px 12px", borderRadius: 16,
                border: `1px solid ${persona === p.name ? V400 : S100}`,
                background: persona === p.name ? V50 : "transparent", cursor: "pointer",
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 500, color: S800 }}>
                {p.name}
                {persona === p.name && <span style={{ marginLeft: 8, fontSize: 11, color: V500 }}>当前</span>}
              </div>
              {p.description && (
                <div
                  style={{
                    fontSize: 12, color: S400, marginTop: 2,
                    display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {p.description}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

// ----------------------------------------------------------------- 模型 //

function ModelPanel({
  llmSelection,
  onSetLLM,
  onBack,
}: ChatPlusPanelProps & { onBack: () => void }) {
  const [options, setOptions] = useState<
    { profile_id: string; model_id: string; profile_name: string; model_name: string; provider: string; is_active_default: boolean }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    listLLMOptions()
      .then((d) => alive && setOptions(d.options || []))
      .catch((e) => alive && setErr(e?.message || "加载失败"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <>
      <SheetHeader title="🤖 模型" onBack={onBack} />
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
          <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
        </div>
      ) : err ? (
        <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>{err}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="model-list">
          <button
            onClick={() => {
              onSetLLM(null);
              onBack();
            }}
            style={{
              width: "100%", textAlign: "left", padding: "12px 12px", borderRadius: 16,
              border: `1px solid ${!llmSelection ? V400 : S100}`,
              background: !llmSelection ? V50 : "transparent", cursor: "pointer",
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 500 }}>跟随默认</div>
          </button>
          {options.map((o) => {
            const active = sameLLMSelection(llmSelection, {
              profile_id: o.profile_id,
              model_id: o.model_id,
            });
            return (
              <button
                key={`${o.profile_id}:${o.model_id}`}
                onClick={() => {
                  onSetLLM({ profile_id: o.profile_id, model_id: o.model_id });
                  onBack();
                }}
                className={active ? "" : "cpp-row"}
                style={{
                  width: "100%", textAlign: "left", padding: "12px 12px", borderRadius: 16,
                  border: `1px solid ${active ? V400 : S100}`,
                  background: active ? V50 : "transparent", cursor: "pointer",
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 500, color: S800, display: "flex", alignItems: "center", gap: 6 }}>
                  {o.model_name}
                  {o.is_active_default && (
                    <span
                      style={{
                        fontSize: 10, padding: "2px 6px", borderRadius: 999,
                        background: "#d1fae5", color: "#059669",
                      }}
                    >
                      默认
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: S400, marginTop: 2 }}>
                  {o.provider} · {o.profile_name}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}

// ----------------------------------------------------------------- 工具 //

const TOOL_LABELS: Record<string, string> = {
  brainstorm: "头脑风暴",
  web_search: "联网搜索",
  paper_search: "论文检索",
  reason: "深度推理",
  imagegen: "图片生成",
  videogen: "视频生成",
  code_execution: "代码执行",
};

function ToolsPanel({
  tools,
  onSetTools,
  onBack,
}: ChatPlusPanelProps & { onBack: () => void }) {
  const [available, setAvailable] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getEnabledOptionalTools()
      .then((list) => alive && setAvailable(list))
      .catch(() => alive && setAvailable([]))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const toggle = (t: string) => {
    const next = tools.includes(t) ? tools.filter((x) => x !== t) : [...tools, t];
    onSetTools(next);
  };

  return (
    <>
      <SheetHeader title="🔧 工具开关" onBack={onBack} />
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
          <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
        </div>
      ) : available.length === 0 ? (
        <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>
          没有可选工具（可在桌面「设置 → 工具」开启）
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="tools-list">
          {available.map((t) => {
            const on = tools.includes(t);
            return (
              <button
                key={t}
                onClick={() => toggle(t)}
                className="cpp-row"
                style={{
                  width: "100%", display: "flex", alignItems: "center",
                  justifyContent: "space-between", padding: "12px 12px",
                  borderRadius: 16, border: `1px solid ${S100}`, cursor: "pointer",
                  background: "transparent",
                }}
              >
                <span style={{ fontSize: 14, color: S800 }}>{TOOL_LABELS[t] || t}</span>
                <span
                  style={{
                    width: 40, height: 24, borderRadius: 999, position: "relative",
                    transition: "background-color .15s", background: on ? "#10b981" : S200,
                  }}
                >
                  <span
                    style={{
                      position: "absolute", top: 2, width: 20, height: 20,
                      borderRadius: 999, background: "#ffffff",
                      boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", transition: "all .15s",
                      left: on ? 18 : 2,
                    }}
                  />
                </span>
              </button>
            );
          })}
        </div>
      )}
      <div style={{ fontSize: 12, color: S400, marginTop: 8 }}>
        基础工具（提问/记忆/笔记本等）由系统按上下文自动挂载，无需手动开启。
      </div>
    </>
  );
}

// ---------------------------------------------------------------- 知识库 //

function KbPanel({ kbs, onSetKBs, onBack }: ChatPlusPanelProps & { onBack: () => void }) {
  const [list, setList] = useState<{ name: string; available?: boolean }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    listKnowledgeBases()
      .then((data: any) => {
        const items = Array.isArray(data) ? data : data?.kbs || data?.items || [];
        alive && setList(items);
      })
      .catch(() => alive && setList([]))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const toggle = (name: string) => {
    onSetKBs(kbs.includes(name) ? kbs.filter((x) => x !== name) : [...kbs, name]);
  };

  return (
    <>
      <SheetHeader title="📚 知识库" onBack={onBack} />
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
          <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
        </div>
      ) : list.length === 0 ? (
        <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>还没有知识库</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="kb-list">
          {list.map((kb) => {
            const on = kbs.includes(kb.name);
            return (
              <button
                key={kb.name}
                onClick={() => toggle(kb.name)}
                className={on ? "" : "cpp-row"}
                style={{
                  width: "100%", display: "flex", alignItems: "center",
                  justifyContent: "space-between", padding: "12px 12px",
                  borderRadius: 16, cursor: "pointer",
                  border: `1px solid ${on ? V400 : S100}`,
                  background: on ? V50 : "transparent",
                }}
              >
                <span
                  style={{
                    fontSize: 14, color: S800, textAlign: "left",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}
                >
                  {kb.name}
                </span>
                {on && <CheckOutlined style={{ fontSize: 14, color: V500, flexShrink: 0 }} />}
              </button>
            );
          })}
        </div>
      )}
      <button
        onClick={onBack}
        style={{
          marginTop: 12, width: "100%", padding: "12px 0", borderRadius: 16,
          background: V600, color: "#ffffff", fontSize: 14, fontWeight: 500,
          border: "none", cursor: "pointer",
        }}
      >
        完成（已选 {kbs.length} 个）
      </button>
    </>
  );
}

// ------------------------------------------------------------ 笔记本引用 //

function NotebookPanel({
  notebookRefs,
  onSetNotebookRefs,
  onBack,
}: ChatPlusPanelProps & { onBack: () => void }) {
  const [notebooks, setNotebooks] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeNb, setActiveNb] = useState<string | null>(null);
  const [records, setRecords] = useState<{ id: string; title: string }[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  // 草稿：notebookId -> 选中的 record ids
  const [draft, setDraft] = useState<Map<string, Set<string>>>(() => {
    const m = new Map<string, Set<string>>();
    for (const ref of notebookRefs) m.set(ref.notebook_id, new Set(ref.record_ids));
    return m;
  });

  useEffect(() => {
    let alive = true;
    listNotebooks()
      .then((nbs) => alive && setNotebooks(nbs.map((n) => ({ id: n.id, name: n.name }))))
      .catch(() => alive && setNotebooks([]))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!activeNb) return;
    setRecordsLoading(true);
    let alive = true;
    getNotebook(activeNb)
      .then((d) => alive && setRecords((d.records || []).map((r) => ({ id: r.id, title: r.title || r.user_query || "（无标题）" }))))
      .catch(() => alive && setRecords([]))
      .finally(() => alive && setRecordsLoading(false));
    return () => {
      alive = false;
    };
  }, [activeNb]);

  const toggleRecord = (rid: string) => {
    if (!activeNb) return;
    const next = new Map(draft);
    const set = new Set(next.get(activeNb) || []);
    if (set.has(rid)) set.delete(rid);
    else set.add(rid);
    if (set.size === 0) next.delete(activeNb);
    else next.set(activeNb, set);
    setDraft(next);
  };

  const apply = () => {
    const payload: NotebookRefPayload[] = Array.from(draft.entries())
      .filter(([, ids]) => ids.size > 0)
      .map(([notebook_id, ids]) => ({ notebook_id, record_ids: Array.from(ids) }));
    onSetNotebookRefs(payload);
    onBack();
  };

  const totalSelected = Array.from(draft.values()).reduce((s, set) => s + set.size, 0);

  if (!activeNb) {
    return (
      <>
        <SheetHeader title="📓 笔记本引用" onBack={onBack} />
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
            <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
          </div>
        ) : notebooks.length === 0 ? (
          <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>还没有笔记本</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {notebooks.map((nb) => (
              <button
                key={nb.id}
                onClick={() => setActiveNb(nb.id)}
                className="cpp-row"
                style={{
                  width: "100%", display: "flex", alignItems: "center",
                  justifyContent: "space-between", padding: "12px 12px",
                  borderRadius: 16, border: `1px solid ${S100}`, cursor: "pointer",
                  background: "transparent",
                }}
              >
                <span style={{ fontSize: 14, color: S800 }}>{nb.name}</span>
                <span style={{ fontSize: 12, color: S400 }}>
                  {(draft.get(nb.id)?.size || 0) > 0 ? `已选 ${draft.get(nb.id)!.size} 条` : "选择记录 ›"}
                </span>
              </button>
            ))}
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <SheetHeader title={`📓 ${notebooks.find((n) => n.id === activeNb)?.name || "笔记本"}`} onBack={() => setActiveNb(null)} />
      {recordsLoading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
          <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载记录…
        </div>
      ) : records.length === 0 ? (
        <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>该笔记本还没有记录</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {records.map((r) => {
            const on = draft.get(activeNb)?.has(r.id);
            return (
              <button
                key={r.id}
                onClick={() => toggleRecord(r.id)}
                className={on ? "" : "cpp-row"}
                style={{
                  width: "100%", display: "flex", alignItems: "center", gap: 8,
                  padding: "12px 12px", borderRadius: 16, textAlign: "left", cursor: "pointer",
                  border: `1px solid ${on ? V400 : S100}`, background: on ? V50 : "transparent",
                }}
              >
                <FileTextOutlined style={{ fontSize: 16, color: S400, flexShrink: 0 }} />
                <span
                  style={{
                    flex: 1, fontSize: 14, color: S800,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}
                >
                  {r.title}
                </span>
                {on && <CheckOutlined style={{ fontSize: 14, color: V500, flexShrink: 0 }} />}
              </button>
            );
          })}
        </div>
      )}
      <button
        onClick={apply}
        style={{
          marginTop: 12, width: "100%", padding: "12px 0", borderRadius: 16,
          background: V600, color: "#ffffff", fontSize: 14, fontWeight: 500,
          border: "none", cursor: "pointer",
        }}
      >
        完成（共引用 {totalSelected} 条）
      </button>
    </>
  );
}

// ---------------------------------------------------------------- 书引用 //

function BookPanel({
  bookRefs,
  onSetBookRefs,
  u,
  onBack,
}: ChatPlusPanelProps & { u: string; onBack: () => void }) {
  const [books, setBooks] = useState<{ id: string; title: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeBook, setActiveBook] = useState<string | null>(null);
  const [chapters, setChapters] = useState<{ id: string; title: string; page_ids: string[] }[]>([]);
  const [pages, setPages] = useState<{ id: string; title: string }[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  // 草稿：bookId -> 选中的 pageIds（空集 = 整本书？桌面语义必须选页）
  const [draft, setDraft] = useState<Map<string, Set<string>>>(() => {
    const m = new Map<string, Set<string>>();
    for (const ref of bookRefs) m.set(ref.bookId, new Set(ref.pages.map((p) => p.pageId)));
    return m;
  });

  useEffect(() => {
    let alive = true;
    bookApi
      .list()
      .then((data: any) => alive && setBooks((data.books || []).map((b: any) => ({ id: b.id, title: b.title || b.name || b.id }))))
      .catch(() => alive && setBooks([]))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!activeBook) return;
    setDetailLoading(true);
    let alive = true;
    bookApi
      .get(activeBook)
      .then((d: any) => {
        if (!alive) return;
        setChapters(
          (d.spine?.chapters || []).map((c: any) => ({
            id: c.id,
            title: c.title,
            page_ids: c.page_ids || [],
          })),
        );
        setPages((d.pages || []).map((p: any) => ({ id: p.id, title: p.title || p.id })));
      })
      .catch(() => {
        if (alive) {
          setChapters([]);
          setPages([]);
        }
      })
      .finally(() => alive && setDetailLoading(false));
    return () => {
      alive = false;
    };
  }, [activeBook]);

  const togglePage = (pid: string) => {
    if (!activeBook) return;
    const next = new Map(draft);
    const set = new Set(next.get(activeBook) || []);
    if (set.has(pid)) set.delete(pid);
    else set.add(pid);
    if (set.size === 0) next.delete(activeBook);
    else next.set(activeBook, set);
    setDraft(next);
  };

  const toggleChapter = (ch: { page_ids: string[] }) => {
    if (!activeBook) return;
    const next = new Map(draft);
    const set = new Set(next.get(activeBook) || []);
    const allOn = ch.page_ids.every((p) => set.has(p));
    for (const p of ch.page_ids) {
      if (allOn) set.delete(p);
      else set.add(p);
    }
    if (set.size === 0) next.delete(activeBook);
    else next.set(activeBook, set);
    setDraft(next);
  };

  const apply = () => {
    const refs: SelectedBookReference[] = [];
    // tupu tsconfig 目标低于 es2015，Map 迭代器需 Array.from 展开（语义不变）。
    for (const [bookId, pageSet] of Array.from(draft.entries())) {
      if (pageSet.size === 0) continue;
      const bookTitle = books.find((b) => b.id === bookId)?.title || bookId;
      refs.push({
        bookId,
        bookTitle,
        pages: Array.from(pageSet).map((pageId) => ({
          bookId,
          bookTitle,
          pageId,
          pageTitle: pages.find((p) => p.id === pageId)?.title || pageId,
        })),
      });
    }
    onSetBookRefs(refs);
    onBack();
  };

  const totalSelected = Array.from(draft.values()).reduce((s, set) => s + set.size, 0);

  if (!activeBook) {
    return (
      <>
        <SheetHeader title="📖 书引用" onBack={onBack} />
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
            <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载中…
          </div>
        ) : books.length === 0 ? (
          <div style={{ fontSize: 14, color: S400, padding: "24px 0", textAlign: "center" }}>
            还没有内部书
            <div style={{ marginTop: 8 }}>
              <Link to={withU("/e/tutor/h5/learn", u)} style={{ color: "#6366f1", textDecoration: "underline" }}>
                去学习页看看教材
              </Link>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {books.map((b) => (
              <button
                key={b.id}
                onClick={() => setActiveBook(b.id)}
                className="cpp-row"
                style={{
                  width: "100%", display: "flex", alignItems: "center",
                  justifyContent: "space-between", padding: "12px 12px",
                  borderRadius: 16, border: `1px solid ${S100}`, cursor: "pointer",
                  background: "transparent",
                }}
              >
                <span
                  style={{
                    fontSize: 14, color: S800,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}
                >
                  {b.title}
                </span>
                <span style={{ fontSize: 12, color: S400, flexShrink: 0, marginLeft: 8 }}>
                  {(draft.get(b.id)?.size || 0) > 0 ? `已选 ${draft.get(b.id)!.size} 页` : "选择页 ›"}
                </span>
              </button>
            ))}
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <SheetHeader title={`📖 ${books.find((b) => b.id === activeBook)?.title || ""}`} onBack={() => setActiveBook(null)} />
      {detailLoading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: S400, fontSize: 14 }}>
          <LoadingOutlined style={{ fontSize: 16, marginRight: 8 }} spin /> 加载书…
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {chapters.map((ch) => (
            <div key={ch.id}>
              <button
                onClick={() => toggleChapter(ch)}
                style={{
                  width: "100%", display: "flex", alignItems: "center",
                  justifyContent: "space-between", padding: "8px 12px", borderRadius: 12,
                  background: S50, textAlign: "left", border: "none", cursor: "pointer",
                }}
              >
                <span
                  style={{
                    fontSize: 12, fontWeight: 600, color: S600,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}
                >
                  {ch.title}
                </span>
                <span style={{ fontSize: 11, color: "#6366f1", flexShrink: 0, marginLeft: 8 }}>整章选/取消</span>
              </button>
              <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 4 }}>
                {ch.page_ids
                  .map((pid) => pages.find((p) => p.id === pid))
                  .filter(Boolean)
                  .map((p) => {
                    const on = draft.get(activeBook!)?.has(p!.id);
                    return (
                      <button
                        key={p!.id}
                        onClick={() => togglePage(p!.id)}
                        style={{
                          width: "100%", display: "flex", alignItems: "center",
                          justifyContent: "space-between", padding: "8px 12px",
                          borderRadius: 12, textAlign: "left", cursor: "pointer",
                          border: `1px solid ${on ? V400 : S100}`, background: on ? V50 : "transparent",
                        }}
                      >
                        <span
                          style={{
                            fontSize: 14, color: S700,
                            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                          }}
                        >
                          {p!.title}
                        </span>
                        {on && <CheckOutlined style={{ fontSize: 14, color: V500, flexShrink: 0 }} />}
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
          {chapters.length === 0 && (
            <div style={{ fontSize: 14, color: S400, padding: "16px 0", textAlign: "center" }}>该书暂无章节页</div>
          )}
        </div>
      )}
      <button
        onClick={apply}
        style={{
          marginTop: 12, width: "100%", padding: "12px 0", borderRadius: 16,
          background: V600, color: "#ffffff", fontSize: 14, fontWeight: 500,
          border: "none", cursor: "pointer",
        }}
      >
        完成（共引用 {totalSelected} 页）
      </button>
    </>
  );
}

// ----------------------------------------------------------------- 语言 //

function LanguagePanel({
  onBack,
  onClose,
}: ChatPlusPanelProps & { onBack: () => void; onClose: () => void }) {
  const [lang, setLang] = useState<string>("en");
  useEffect(() => {
    setLang(readStoredLanguage());
  }, []);
  const pick = (l: "zh" | "en") => {
    writeStoredLanguage(l);
    setLang(l);
    onClose();
  };
  return (
    <>
      <SheetHeader title="🌐 语言" onBack={onBack} />
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="language-list">
        <button
          onClick={() => pick("zh")}
          style={{
            width: "100%", textAlign: "left", padding: "12px 12px", borderRadius: 16,
            border: `1px solid ${lang === "zh" ? V400 : S100}`,
            background: lang === "zh" ? V50 : "transparent", cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 500 }}>中文</div>
        </button>
        <button
          onClick={() => pick("en")}
          style={{
            width: "100%", textAlign: "left", padding: "12px 12px", borderRadius: 16,
            border: `1px solid ${lang === "en" ? V400 : S100}`,
            background: lang === "en" ? V50 : "transparent", cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 500 }}>English</div>
        </button>
      </div>
    </>
  );
}

export { selectedBooksToPayload };
