/**
 * 检索引擎详情页（复刻 DeepTutor web/components/knowledge/EngineDetail.tsx → tupu antd 5）。
 *
 * 区块（与源逐块对应，顺序不变）：
 *   返回（知识中心）→ 引擎头（图标+名称+状态徽标+描述）→ 环境要求（可折叠：前置说明 +
 *   安装命令复制 + 「检查环境」preflight 检查列表——可选项不阻断语义）→
 *   检索模式（modes + default_mode，卡片点选即 onSelectMode）→ 检索与分块（llamaindex）→
 *   检索参数（graphrag / lightrag）→ 凭证（pageindex）→ 模型选择器（llm+embedding，active-model）→
 *   该引擎知识库列表（onOpenKb）。
 *
 * 映射说明：
 *   - lucide → @ant-design/icons 最近图标：Boxes→AppstoreOutlined、Network→ApartmentOutlined、
 *     Workflow→DeploymentUnitOutlined、Server→CloudServerOutlined、Settings2→ControlOutlined、
 *     ShieldCheck→SafetyCertificateOutlined、CircleSlash→MinusCircleOutlined、Loader2→LoadingOutlined；
 *   - tailwind → antd props + style（颜色走 theme/tokens：emerald→success、amber→warning、red→error、
 *     muted→textSecondary/bgSubtle；源 /settings「模型目录」链接 → tupu /llm-config）；
 *   - 文案：t('English') → 中文（zh/app.json 收录键）；MODE_DESCRIPTIONS / ENGINE_PREREQUISITES /
 *     检索画像描述照搬英文原文键，渲染经 ZH 覆盖表取中文；未收录键（lightrag-server:mix）保留
 *     英文原文——与源 i18n fallback 语义一致；
 *   - KnowledgeBase 类型与 kbProvider/kbDocCount/resolveKbStatus 语义照搬源 lib/knowledge-helpers.ts
 *     （源经 props 传入，此处自包含定义，不新增文件依赖）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Button, Col, Input, InputNumber, Row, Select, Spin, Switch } from 'antd';
import {
  ApartmentOutlined,
  AppstoreOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CheckOutlined,
  CloseCircleOutlined,
  CloudOutlined,
  CloudServerOutlined,
  ControlOutlined,
  CopyOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  DownOutlined,
  ExportOutlined,
  KeyOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import {
  getEngineModelOptions,
  getEnginePreflight,
  getGraphRagConfig,
  getLightRagConfig,
  getLlamaIndexConfig,
  getPageIndexConfig,
  setEngineActiveModel,
  updateGraphRagConfig,
  updateLightRagConfig,
  updateLlamaIndexConfig,
  updatePageIndexConfig,
  type EnginePreflight,
  type GraphRagConfig,
  type LightRagConfig,
  type LlamaIndexConfig,
  type ModelOptionsByKind,
  type PageIndexConfig,
  type RagProviderSummary,
} from './knowledge-api';
import { colors } from '../../theme/tokens';

interface EngineDetailProps {
  provider: RagProviderSummary;
  kbs: KnowledgeBase[];
  onBack: () => void;
  onOpenKb: (name: string) => void;
  onSelectMode: (providerId: string, mode: string) => Promise<void> | void;
  /** Called after a config change so the parent can refresh provider state. */
  onChanged: () => void;
  onError: (message: string) => void;
}

/* ------------------------------ 共享视觉常量 ------------------------------ */

const SERIF = "Georgia, 'Times New Roman', 'Songti SC', SimSun, serif";
const MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace";
const CARD_BORDER = `1px solid ${colors.border}`;
/** 模型目录入口：源指向 /settings，tupu 对应 LLM 配置页。 */
const MODEL_CATALOG_PATH = '/llm-config';

type IconComponent = React.ComponentType<{ style?: React.CSSProperties }>;

const ENGINE_ICONS: Record<string, IconComponent> = {
  llamaindex: AppstoreOutlined,
  pageindex: CloudOutlined,
  graphrag: ApartmentOutlined,
  lightrag: DeploymentUnitOutlined,
  'lightrag-server': CloudServerOutlined,
};

const INSTALL_HINTS: Record<string, string> = {
  graphrag: "pip install 'deeptutor[graphrag]'",
  lightrag: "pip install 'deeptutor[rag-lightrag]'",
};

// Mode one-liners, keyed by `${engineId}:${mode}`. English source strings double
// as i18n keys (zh translations live in locales/zh/app.json).
const MODE_DESCRIPTIONS: Record<string, string> = {
  'graphrag:local':
    'Entity-focused retrieval over the relevant local subgraph — fast and economical.',
  'graphrag:global':
    'Map-reduce over global community summaries — best for broad, thematic questions.',
  'graphrag:drift':
    'Local retrieval with dynamic follow-ups — balances precision and coverage.',
  'graphrag:basic': 'Plain vector retrieval — the lightest option.',
  'lightrag:naive': 'Plain vector retrieval, without the knowledge graph.',
  'lightrag:local': 'Local context focused on the most relevant entities.',
  'lightrag:global': 'Theme-level retrieval over global relationships.',
  'lightrag:hybrid':
    'Combines local and global retrieval — a solid general default.',
  'lightrag:mix': 'Fuses knowledge-graph and vector retrieval.',
  'lightrag-server:naive':
    'Plain vector retrieval, without the knowledge graph.',
  'lightrag-server:local':
    'Local context focused on the most relevant entities.',
  'lightrag-server:global': 'Theme-level retrieval over global relationships.',
  'lightrag-server:hybrid':
    'Combines local and global retrieval — a solid general default.',
  'lightrag-server:mix':
    "Fuses knowledge-graph and vector retrieval — the server's default.",
};

/** zh/app.json 已收录键的中文覆盖；未收录（lightrag-server:mix）回退英文原文。 */
const MODE_DESCRIPTIONS_ZH: Record<string, string> = {
  'graphrag:local': '以实体为中心，在相关局部子图上检索——更快、更省。',
  'graphrag:global': '对全局社区摘要做 map-reduce——最适合宽泛的主题型问题。',
  'graphrag:drift': '局部检索 + 动态跟进——兼顾精确与覆盖。',
  'graphrag:basic': '朴素向量检索——最轻量的选项。',
  'lightrag:naive': '朴素向量检索，不使用知识图谱。',
  'lightrag:local': '聚焦最相关实体的局部上下文。',
  'lightrag:global': '基于全局关系的主题级检索。',
  'lightrag:hybrid': '结合局部与全局检索——稳妥的通用默认。',
  'lightrag:mix': '融合知识图谱与向量检索。',
  'lightrag-server:naive': '朴素向量检索，不使用知识图谱。',
  'lightrag-server:local': '聚焦最相关实体的局部上下文。',
  'lightrag-server:global': '基于全局关系的主题级检索。',
  'lightrag-server:hybrid': '结合局部与全局检索——稳妥的通用默认。',
};

// Model kinds each engine needs (for the in-place pickers). "vision" isn't a
// catalog service — it rides on the active chat model — so LightRAG only lists
// llm + embedding and shows a vision note under the chat picker. LightRAG Server
// owns its own models on the remote instance, so it needs none here.
const ENGINE_MODEL_KINDS: Record<string, ('llm' | 'embedding')[]> = {
  llamaindex: ['embedding'],
  pageindex: [],
  graphrag: ['llm', 'embedding'],
  lightrag: ['llm', 'embedding'],
  'lightrag-server': [],
};

const MODEL_KIND_LABEL: Record<string, string> = {
  llm: 'Chat model',
  embedding: 'Embedding model',
};

const MODEL_KIND_LABEL_ZH: Record<string, string> = {
  llm: '对话模型',
  embedding: '嵌入模型',
};

// Free-form GraphRAG/LightRAG answer styles. Any string is accepted server-side;
// these are the common presets.
const RESPONSE_TYPE_PRESETS = [
  'Multiple Paragraphs',
  'Single Paragraph',
  'Single Sentence',
  'List of 3-7 Points',
  'Multiple-Page Report',
];

// Prerequisites prose per engine (English source doubles as i18n key).
const ENGINE_PREREQUISITES: Record<string, string> = {
  llamaindex:
    'Local vector engine — works out of the box. Retrieval uses your active embedding model; install the optional BM25 package to enable hybrid retrieval.',
  pageindex:
    "Hosted engine: documents are uploaded to PageIndex's servers and the chat agent reads them through the PageIndex MCP tools. Requires an API key; PDF, Office, text and Markdown formats.",
  graphrag:
    'Local knowledge-graph retrieval. Needs the optional dependency installed; indexing is LLM-heavy. Requires an active chat model and embedding model.',
  lightrag:
    'Graph + vector retrieval with multimodal parsing. Needs the optional dependency installed; indexing is LLM-heavy. Requires active chat and embedding models; multimodal also needs a vision model.',
};

/** zh 覆盖（zh/app.json 收录）；缺失时回退英文原文。 */
const ENGINE_PREREQUISITES_ZH: Record<string, string> = {
  llamaindex:
    '本地向量引擎，开箱即用。检索使用你当前启用的嵌入模型；可选安装 BM25 包以启用混合检索。',
  pageindex:
    '托管引擎：文档上传到 PageIndex 服务器，聊天 agent 通过 PageIndex MCP 工具阅读文档。需配置 API 密钥；支持 PDF、Office、文本和 Markdown 格式。',
  graphrag:
    '本地知识图谱检索。需要安装可选依赖；索引为 LLM 密集型操作。需启用对话模型与嵌入模型。',
  lightrag:
    '图 + 向量检索，支持多模态解析。需要安装可选依赖；索引为 LLM 密集型操作。需启用对话与嵌入模型；多模态还需视觉模型。',
};

/* --------------------- KnowledgeBase 最小类型 + helpers -------------------- */
/* 语义照搬源 web/lib/knowledge-helpers.ts（本文件只用到这三个）。 */

export interface ProgressInfo {
  task_id?: string;
  stage?: string;
  message?: string;
  current?: number;
  total?: number;
  percent?: number;
  progress_percent?: number;
  indexed_count?: number;
  index_changed?: boolean;
  index_action?: string;
}

export interface IndexVersion {
  signature?: string;
  model?: string;
  dimension?: number;
  binding?: string;
  created_at?: string;
  ready?: boolean;
  legacy?: boolean;
}

export interface KnowledgeBase {
  id?: string;
  name: string;
  is_default?: boolean;
  status?: string;
  path?: string;
  metadata?: {
    created_at?: string;
    last_updated?: string;
    last_indexed_at?: string;
    last_indexed_count?: number;
    last_indexed_action?: string;
    rag_provider?: string;
    needs_reindex?: boolean;
    embedding_model?: string;
    embedding_dim?: number;
    embedding_mismatch?: boolean;
    /** Connected-source kind (e.g. "obsidian", "subagent"); absent for ordinary indexed KBs. */
    type?: string;
    /** Absolute path of a connected Obsidian vault (when type === "obsidian"). */
    vault_path?: string;
    /** Backend of a connected subagent (when type === "subagent"): "claude_code" | "codex" | "gemini" | "kimi" | "opencode" | "mimo" | "partner". */
    agent_kind?: string;
    /** Bound partner id when agent_kind === "partner". */
    partner_id?: string;
  };
  progress?: ProgressInfo;
  statistics?: {
    raw_documents?: number;
    images?: number;
    content_lists?: number;
    rag_provider?: string;
    rag_initialized?: boolean;
    needs_reindex?: boolean;
    status?: string;
    progress?: ProgressInfo;
    index_versions?: IndexVersion[];
    active_signature?: string | null;
    active_match?: boolean;
  };
  source?: 'admin' | 'user';
  assigned?: boolean;
  read_only?: boolean;
  provenance_label?: string;
  available?: boolean;
}

/** The retrieval engine a KB is bound to. Connected vaults badge by source. */
export const kbProvider = (kb: KnowledgeBase): string => {
  if (kb.metadata?.type === 'obsidian') return 'obsidian';
  return (
    (kb.statistics?.rag_provider as string | undefined) ||
    (kb.metadata?.rag_provider as string | undefined) ||
    'llamaindex'
  );
};

/** Source-document count for a KB, or null when unknown. */
export const kbDocCount = (kb: KnowledgeBase): number | null => {
  const raw = kb.statistics?.raw_documents;
  if (typeof raw === 'number') return raw;
  const indexed = kb.metadata?.last_indexed_count;
  return typeof indexed === 'number' ? indexed : null;
};

export const resolveKbStatus = (kb: KnowledgeBase): string =>
  kb.status ?? kb.statistics?.status ?? 'unknown';

/* ------------------------------- 引擎 3 态 -------------------------------- */

type EngineStatus = 'ready' | 'needs_key' | 'unavailable';

function resolveStatus(provider: RagProviderSummary): EngineStatus {
  if (provider.requires_api_key && provider.configured === false)
    return 'needs_key';
  if (provider.configured === false) return 'unavailable';
  return 'ready';
}

function StatusBadge({ status }: { status: EngineStatus }) {
  const base: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    borderRadius: 999,
    padding: '2px 8px',
    fontSize: '10.5px',
    fontWeight: 500,
    lineHeight: 1.6,
  };
  if (status === 'ready') {
    return (
      <span style={{ ...base, background: colors.successBg, color: colors.success }}>
        <CheckOutlined style={{ fontSize: 12 }} />
        就绪
      </span>
    );
  }
  if (status === 'needs_key') {
    return (
      <span style={{ ...base, background: colors.warningBg, color: colors.warning }}>
        需配置密钥
      </span>
    );
  }
  return (
    <span style={{ ...base, background: colors.bgSubtle, color: colors.textSecondary }}>
      未安装
    </span>
  );
}

/** Section shell: small uppercase label + bordered card body. */
function Section({
  label,
  icon: Icon,
  children,
}: {
  label: string;
  icon: IconComponent;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginTop: 28 }}>
      <h2
        style={{
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          fontSize: 11,
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: colors.textSecondary,
        }}
      >
        <Icon style={{ fontSize: 14 }} />
        {label}
      </h2>
      {children}
    </section>
  );
}

function CopyableCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        borderRadius: 8,
        border: CARD_BORDER,
        background: 'rgba(249, 250, 251, 0.4)',
        padding: '8px 12px',
      }}
    >
      <code
        style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          fontFamily: MONO,
          fontSize: 12,
          color: colors.textPrimary,
        }}
      >
        {command}
      </code>
      <Button
        type="text"
        size="small"
        onClick={() => {
          void navigator.clipboard?.writeText(command);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1500);
        }}
        icon={copied ? <CheckOutlined style={{ fontSize: 12 }} /> : <CopyOutlined style={{ fontSize: 12 }} />}
        style={{ flexShrink: 0, fontSize: 11, fontWeight: 500, color: colors.textSecondary, height: 'auto', padding: '2px 6px' }}
      >
        {copied ? '已复制' : '复制'}
      </Button>
    </div>
  );
}

/** Number field used by the LlamaIndex tuning form（源 number input → antd InputNumber）。 */
function NumberField({
  label,
  hint,
  value,
  min,
  max,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  onChange: (next: number) => void;
  disabled?: boolean;
}) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 12, fontWeight: 500, color: colors.textPrimary }}>{label}</span>
      <InputNumber
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        style={{ width: '100%' }}
        onChange={(v) => onChange(v ?? min)}
      />
      {hint && <span style={{ fontSize: 11, color: colors.textSecondary }}>{hint}</span>}
    </label>
  );
}

/** 卡片单选格（源 button 卡片：hover 描边 + 选中主色浅底）。 */
function PickCard({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        borderRadius: 12,
        border: `1px solid ${active ? colors.primary : hover ? colors.borderStrong : colors.border}`,
        background: active ? colors.primaryBg : 'transparent',
        padding: 12,
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'border-color 0.2s, background 0.2s',
        width: '100%',
      }}
    >
      {children}
    </button>
  );
}

/* ----------------------------- Mode selector ----------------------------- */

function ModeSelector({
  provider,
  onSelectMode,
}: {
  provider: RagProviderSummary;
  onSelectMode: (providerId: string, mode: string) => Promise<void> | void;
}) {
  const modes = useMemo(() => provider.modes ?? [], [provider.modes]);
  const [selected, setSelected] = useState(
    provider.default_mode || modes[0] || '',
  );
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    setSelected(provider.default_mode || modes[0] || '');
  }, [provider.default_mode, modes]);

  const pick = async (mode: string) => {
    if (mode === selected) return;
    setSelected(mode);
    setPending(mode);
    try {
      await onSelectMode(provider.id, mode);
    } finally {
      setPending(null);
    }
  };

  return (
    <Row gutter={[8, 8]}>
      {modes.map((mode) => {
        const active = mode === selected;
        const key = `${provider.id}:${mode}`;
        const desc = MODE_DESCRIPTIONS[key];
        return (
          <Col xs={24} sm={12} key={mode}>
            <PickCard active={active} onClick={() => void pick(mode)}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontFamily: MONO, fontSize: '12.5px', fontWeight: 500, color: colors.textPrimary }}>
                  {mode}
                </span>
                {pending === mode ? (
                  <LoadingOutlined spin style={{ fontSize: 14, color: colors.textSecondary }} />
                ) : active ? (
                  <CheckOutlined style={{ fontSize: 14, color: colors.primary }} />
                ) : null}
              </div>
              {desc && (
                <span style={{ fontSize: '11.5px', lineHeight: 1.4, color: colors.textSecondary }}>
                  {MODE_DESCRIPTIONS_ZH[key] ?? desc}
                </span>
              )}
            </PickCard>
          </Col>
        );
      })}
    </Row>
  );
}

/* -------------------------- LlamaIndex config form ------------------------ */

function LlamaIndexForm({
  onChanged,
  onError,
}: {
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const [loaded, setLoaded] = useState<LlamaIndexConfig | null>(null);
  const [form, setForm] = useState<LlamaIndexConfig | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getLlamaIndexConfig({ force: true })
      .then((cfg) => {
        if (cancelled) return;
        setLoaded(cfg);
        setForm(cfg);
      })
      .catch((err) =>
        onError(err instanceof Error ? err.message : String(err)),
      );
    return () => {
      cancelled = true;
    };
    // onError is stable enough; we only want this on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dirty = useMemo(
    () => !!form && !!loaded && JSON.stringify(form) !== JSON.stringify(loaded),
    [form, loaded],
  );

  if (!form) {
    return <FormSkeleton />;
  }

  const set = (patch: Partial<LlamaIndexConfig>) =>
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));

  const save = async () => {
    if (!form) return;
    setSaving(true);
    try {
      const next = await updateLlamaIndexConfig({
        retrieval_profile: form.retrieval_profile,
        top_k: form.top_k,
        vector_top_k_multiplier: form.vector_top_k_multiplier,
        bm25_top_k_multiplier: form.bm25_top_k_multiplier,
        chunk_size: form.chunk_size,
        chunk_overlap: form.chunk_overlap,
      });
      setLoaded(next);
      setForm(next);
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const isHybrid = form.retrieval_profile === 'hybrid';
  const profiles: {
    id: LlamaIndexConfig['retrieval_profile'];
    desc: string;
  }[] = [
    {
      id: 'hybrid',
      desc: 'BM25 keyword + vector semantic retrieval, fused and re-ranked. More robust recall.',
    },
    {
      id: 'vector',
      desc: 'Vector semantic retrieval only. Faster, but leans entirely on embedding quality.',
    },
  ];
  const PROFILE_DESC_ZH: Record<string, string> = {
    hybrid: 'BM25 关键词 + 向量语义检索，融合重排，召回更稳健。',
    vector: '仅向量语义检索，更快，但完全依赖嵌入质量。',
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
        borderRadius: 16,
        border: CARD_BORDER,
        padding: 16,
      }}
    >
      {/* Retrieval profile */}
      <div>
        <div style={{ marginBottom: 8, fontSize: 12, fontWeight: 500, color: colors.textPrimary }}>
          检索画像
        </div>
        <Row gutter={[8, 8]}>
          {profiles.map((p) => {
            const active = form.retrieval_profile === p.id;
            return (
              <Col xs={24} sm={12} key={p.id}>
                <PickCard active={active} onClick={() => set({ retrieval_profile: p.id })}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <span style={{ fontFamily: MONO, fontSize: '12.5px', fontWeight: 500, color: colors.textPrimary }}>
                      {p.id}
                    </span>
                    {active && <CheckOutlined style={{ fontSize: 14, color: colors.primary }} />}
                  </div>
                  <span style={{ fontSize: '11.5px', lineHeight: 1.4, color: colors.textSecondary }}>
                    {PROFILE_DESC_ZH[p.id] ?? p.desc}
                  </span>
                </PickCard>
              </Col>
            );
          })}
        </Row>
      </div>

      {/* Retrieval breadth */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <NumberField
            label="每次查询返回结果数"
            value={form.top_k}
            min={1}
            max={50}
            onChange={(v) => set({ top_k: v })}
          />
        </Col>
        <Col xs={24} sm={8}>
          <NumberField
            label="向量候选倍率"
            hint={isHybrid ? undefined : '仅 hybrid 模式使用'}
            value={form.vector_top_k_multiplier}
            min={1}
            max={10}
            disabled={!isHybrid}
            onChange={(v) => set({ vector_top_k_multiplier: v })}
          />
        </Col>
        <Col xs={24} sm={8}>
          <NumberField
            label="关键词候选倍率"
            hint={isHybrid ? undefined : '仅 hybrid 模式使用'}
            value={form.bm25_top_k_multiplier}
            min={1}
            max={10}
            disabled={!isHybrid}
            onChange={(v) => set({ bm25_top_k_multiplier: v })}
          />
        </Col>
      </Row>

      {/* Chunking */}
      <div>
        <div style={{ marginBottom: 8, display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: colors.textPrimary }}>分块</span>
          <span style={{ fontSize: 11, color: colors.textSecondary }}>下次重新索引时生效</span>
        </div>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <NumberField
              label="分块大小"
              value={form.chunk_size}
              min={64}
              max={8192}
              onChange={(v) => set({ chunk_size: v })}
            />
          </Col>
          <Col xs={24} sm={12}>
            <NumberField
              label="分块重叠"
              value={form.chunk_overlap}
              min={0}
              max={Math.max(0, form.chunk_size - 1)}
              onChange={(v) => set({ chunk_overlap: v })}
            />
          </Col>
        </Row>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="primary"
          onClick={() => void save()}
          disabled={!dirty || saving}
          loading={saving}
          style={{ fontSize: '12.5px', height: 'auto', padding: '6px 14px' }}
        >
          保存更改
        </Button>
      </div>
    </div>
  );
}

/* -------------------------- PageIndex config form ------------------------- */

const PAGEINDEX_DEFAULT_BASE_URL = 'https://api.pageindex.ai';

const PAGEINDEX_DESCRIPTION =
  'PageIndex 是托管的无向量检索引擎。PageIndex 知识库中的文档会上传到 PageIndex 服务器进行处理。同一个密钥由你所有的 PageIndex 知识库共用。';

const KEY_CONFIGURED_PLACEHOLDER = '•••••••• （已配置，留空则保留）';
const KEY_EMPTY_PLACEHOLDER = '输入你的 PageIndex API 密钥';

function PageIndexForm({
  onChanged,
  onError,
}: {
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const [config, setConfig] = useState<PageIndexConfig | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPageIndexConfig({ force: true })
      .then((cfg) => {
        if (cancelled) return;
        setConfig(cfg);
        setBaseUrl(cfg.api_base_url || '');
      })
      .catch((err) =>
        onError(err instanceof Error ? err.message : String(err)),
      );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persist = async (payload: {
    api_key?: string;
    api_base_url?: string;
  }) => {
    setSaving(true);
    try {
      const next = await updatePageIndexConfig(payload);
      setConfig(next);
      setApiKey('');
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const keySet = config?.api_key_set ?? false;
  const fieldLabelStyle: React.CSSProperties = {
    marginBottom: 4,
    display: 'block',
    fontSize: 11,
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: colors.textSecondary,
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        borderRadius: 16,
        border: CARD_BORDER,
        padding: 16,
      }}
    >
      <p style={{ margin: 0, fontSize: 12, lineHeight: 1.7, color: colors.textSecondary }}>
        {PAGEINDEX_DESCRIPTION}
      </p>

      <div>
        <label style={fieldLabelStyle}>API 密钥</label>
        <Input.Password
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          disabled={saving}
          visibilityToggle={false}
          placeholder={keySet ? KEY_CONFIGURED_PLACEHOLDER : KEY_EMPTY_PLACEHOLDER}
        />
        {keySet && (
          <Button
            type="link"
            danger
            onClick={() => void persist({ api_key: '' })}
            disabled={saving}
            style={{ marginTop: 6, fontSize: 11, fontWeight: 500, height: 'auto', padding: 0 }}
          >
            移除已存密钥
          </Button>
        )}
      </div>

      <div>
        <label style={fieldLabelStyle}>API 基础地址</label>
        <Input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          disabled={saving}
          placeholder={PAGEINDEX_DEFAULT_BASE_URL}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <a
          href="https://dash.pageindex.ai/api-keys"
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            fontSize: '11.5px',
            color: colors.textSecondary,
          }}
        >
          获取 API 密钥
          <ExportOutlined style={{ fontSize: 12 }} />
        </a>
        <Button
          type="primary"
          onClick={() =>
            void persist({
              api_base_url: baseUrl.trim() || undefined,
              ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
            })
          }
          disabled={saving}
          loading={saving}
          style={{ fontSize: '12.5px', height: 'auto', padding: '6px 14px' }}
        >
          保存更改
        </Button>
      </div>
    </div>
  );
}

/* --------------------------- Shared form controls ------------------------- */

function ResponseTypeSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (next: string) => void;
}) {
  const known = RESPONSE_TYPE_PRESETS.includes(value);
  const options = RESPONSE_TYPE_PRESETS.map((p) => ({ value: p, label: p }));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 12, fontWeight: 500, color: colors.textPrimary }}>回答样式</span>
      <Select
        value={value}
        onChange={onChange}
        style={{ width: '100%' }}
        options={known ? options : [...options, { value, label: value }]}
      />
    </div>
  );
}

function ToggleField({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: colors.textPrimary }}>{label}</span>
        {hint && <span style={{ fontSize: 11, color: colors.textSecondary }}>{hint}</span>}
      </div>
      <Switch checked={checked} onChange={(next) => onChange(next)} />
    </div>
  );
}

function SaveButton({
  dirty,
  saving,
  onSave,
}: {
  dirty: boolean;
  saving: boolean;
  onSave: () => void;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <Button
        type="primary"
        onClick={onSave}
        disabled={!dirty || saving}
        loading={saving}
        style={{ fontSize: '12.5px', height: 'auto', padding: '6px 14px' }}
      >
        保存更改
      </Button>
    </div>
  );
}

/** Shared loader + dirty-tracking scaffold for the small engine config forms. */
function useEngineForm<T>(
  load: () => Promise<T>,
  onError: (m: string) => void,
) {
  const [loaded, setLoaded] = useState<T | null>(null);
  const [form, setForm] = useState<T | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    load()
      .then((cfg) => {
        if (cancelled) return;
        setLoaded(cfg);
        setForm(cfg);
      })
      .catch((err) =>
        onError(err instanceof Error ? err.message : String(err)),
      );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dirty = useMemo(
    () => !!form && !!loaded && JSON.stringify(form) !== JSON.stringify(loaded),
    [form, loaded],
  );
  const patch = (p: Partial<T>) =>
    setForm((prev) => (prev ? { ...prev, ...p } : prev));
  return { loaded, form, setLoaded, setForm, saving, setSaving, dirty, patch };
}

/* -------------------------- GraphRAG config form -------------------------- */

function GraphRagForm({
  onChanged,
  onError,
}: {
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const { form, setLoaded, setForm, saving, setSaving, dirty, patch } =
    useEngineForm<GraphRagConfig>(
      () => getGraphRagConfig({ force: true }),
      onError,
    );

  if (!form) return <FormSkeleton />;

  const save = async () => {
    setSaving(true);
    try {
      const next = await updateGraphRagConfig({
        response_type: form.response_type,
        community_level: form.community_level,
        dynamic_community_selection: form.dynamic_community_selection,
      });
      setLoaded(next);
      setForm(next);
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        borderRadius: 16,
        border: CARD_BORDER,
        padding: 16,
      }}
    >
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <ResponseTypeSelect
            value={form.response_type}
            onChange={(v) => patch({ response_type: v })}
          />
        </Col>
        <Col xs={24} sm={12}>
          <NumberField
            label="社区层级"
            hint="图谱遍历粒度（local / drift）"
            value={form.community_level}
            min={0}
            max={5}
            onChange={(v) => patch({ community_level: v })}
          />
        </Col>
      </Row>
      <ToggleField
        label="动态社区选择"
        hint="仅 global 模式"
        checked={form.dynamic_community_selection}
        onChange={(v) => patch({ dynamic_community_selection: v })}
      />
      <SaveButton dirty={dirty} saving={saving} onSave={() => void save()} />
    </div>
  );
}

/* -------------------------- LightRAG config form -------------------------- */

function LightRagForm({
  onChanged,
  onError,
}: {
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const { form, setLoaded, setForm, saving, setSaving, dirty, patch } =
    useEngineForm<LightRagConfig>(
      () => getLightRagConfig({ force: true }),
      onError,
    );

  if (!form) return <FormSkeleton />;

  const save = async () => {
    setSaving(true);
    try {
      const next = await updateLightRagConfig({
        top_k: form.top_k,
        response_type: form.response_type,
      });
      setLoaded(next);
      setForm(next);
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        borderRadius: 16,
        border: CARD_BORDER,
        padding: 16,
      }}
    >
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <NumberField
            label="每次查询返回结果数"
            value={form.top_k}
            min={1}
            max={200}
            onChange={(v) => patch({ top_k: v })}
          />
        </Col>
        <Col xs={24} sm={12}>
          <ResponseTypeSelect
            value={form.response_type}
            onChange={(v) => patch({ response_type: v })}
          />
        </Col>
      </Row>
      <SaveButton dirty={dirty} saving={saving} onSave={() => void save()} />
    </div>
  );
}

function FormSkeleton() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 16,
        border: CARD_BORDER,
        padding: '40px 0',
      }}
    >
      <Spin size="small" />
    </div>
  );
}

/* ------------------------------ Model pickers ----------------------------- */

function ModelsSection({
  providerId,
  onError,
}: {
  providerId: string;
  onError: (message: string) => void;
}) {
  const kinds = useMemo(
    () => ENGINE_MODEL_KINDS[providerId] ?? [],
    [providerId],
  );
  const [data, setData] = useState<ModelOptionsByKind | null>(null);
  const [failed, setFailed] = useState(false);
  const [busyKind, setBusyKind] = useState<string | null>(null);

  useEffect(() => {
    if (kinds.length === 0) return;
    let cancelled = false;
    getEngineModelOptions(kinds)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [kinds]);

  const select = useCallback(
    async (kind: string, profileId: string, modelId: string) => {
      setBusyKind(kind);
      try {
        const updated = await setEngineActiveModel(kind, profileId, modelId);
        setData((prev) => (prev ? { ...prev, [kind]: updated } : prev));
      } catch (err) {
        onError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusyKind(null);
      }
    },
    [onError],
  );

  if (kinds.length === 0) return null;

  return (
    <Section label="模型列表" icon={AppstoreOutlined}>
      {failed ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            borderRadius: 16,
            border: CARD_BORDER,
            padding: 16,
          }}
        >
          <p style={{ margin: 0, fontSize: 12, lineHeight: 1.7, color: colors.textSecondary }}>
            此引擎使用你当前启用的对话与嵌入模型，可在模型目录中管理。
          </p>
          <RouterLink
            to={MODEL_CATALOG_PATH}
            style={{
              display: 'inline-flex',
              flexShrink: 0,
              alignItems: 'center',
              gap: 6,
              borderRadius: 8,
              border: CARD_BORDER,
              padding: '6px 12px',
              fontSize: 12,
              fontWeight: 500,
              color: colors.textPrimary,
            }}
          >
            打开模型目录
            <ExportOutlined style={{ fontSize: 12 }} />
          </RouterLink>
        </div>
      ) : !data ? (
        <FormSkeleton />
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            borderRadius: 16,
            border: CARD_BORDER,
            padding: 16,
          }}
        >
          {kinds.map((kind) => {
            const entry = data[kind];
            const value = `${entry?.active.profile_id ?? ''}::${entry?.active.model_id ?? ''}`;
            const hasOptions = (entry?.options.length ?? 0) > 0;
            return (
              <div key={kind} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: colors.textPrimary }}>
                    {MODEL_KIND_LABEL_ZH[kind] ?? MODEL_KIND_LABEL[kind] ?? kind}
                  </span>
                  {busyKind === kind && (
                    <LoadingOutlined spin style={{ fontSize: 12, color: colors.textSecondary }} />
                  )}
                </div>
                {hasOptions ? (
                  <Select
                    value={value === '::' ? undefined : value}
                    disabled={busyKind === kind}
                    style={{ width: '100%' }}
                    onChange={(next) => {
                      const [pid, mid] = next.split('::');
                      void select(kind, pid, mid);
                    }}
                    options={(entry!.options).map((o) => ({
                      value: `${o.profile_id}::${o.model_id}`,
                      label: `${o.label}${o.detail ? ` · ${o.detail}` : ''}`,
                    }))}
                  />
                ) : (
                  <RouterLink
                    to={MODEL_CATALOG_PATH}
                    style={{
                      display: 'inline-flex',
                      width: 'fit-content',
                      alignItems: 'center',
                      gap: 6,
                      borderRadius: 8,
                      border: `1px dashed ${colors.border}`,
                      padding: '6px 12px',
                      fontSize: 12,
                      color: colors.textSecondary,
                    }}
                  >
                    未配置模型 — 打开模型目录
                    <ExportOutlined style={{ fontSize: 12 }} />
                  </RouterLink>
                )}
                {kind === 'llm' && providerId === 'lightrag' && (
                  <span style={{ fontSize: 11, color: colors.textSecondary }}>
                    多模态文档需要支持视觉的对话模型。
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Section>
  );
}

/* ----------------------- Requirements & environment ----------------------- */

function CheckRow({
  ok,
  optional,
  label,
  detail,
}: {
  ok: boolean;
  optional: boolean;
  label: string;
  detail: string;
}) {
  const Icon = ok ? CheckCircleOutlined : optional ? MinusCircleOutlined : CloseCircleOutlined;
  const tone = ok
    ? colors.success
    : optional
      ? colors.textSecondary
      : colors.error;
  return (
    <li style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
      <Icon style={{ marginTop: 2, fontSize: 14, flexShrink: 0, color: tone }} />
      <div style={{ minWidth: 0 }}>
        <span style={{ fontSize: 12, color: colors.textPrimary }}>{label}</span>
        {optional && (
          <span style={{ marginLeft: 6, fontSize: 10, color: colors.textSecondary }}>
            (可选)
          </span>
        )}
        {detail && (
          <div style={{ fontSize: 11, lineHeight: 1.4, color: colors.textSecondary }}>
            {detail}
          </div>
        )}
      </div>
    </li>
  );
}

function EnvRequirements({
  providerId,
  installHint,
  defaultOpen,
  onError,
}: {
  providerId: string;
  installHint?: string;
  defaultOpen: boolean;
  onError: (message: string) => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [report, setReport] = useState<EnginePreflight | null>(null);
  const [checking, setChecking] = useState(false);
  const prereq = ENGINE_PREREQUISITES[providerId];

  const runCheck = async () => {
    setChecking(true);
    try {
      setReport(await getEnginePreflight(providerId));
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setChecking(false);
    }
  };

  return (
    <section style={{ marginTop: 28 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex',
          width: '100%',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderRadius: 8,
          padding: '4px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
        aria-expanded={open}
      >
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 11,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: colors.textSecondary,
          }}
        >
          <SafetyCertificateOutlined style={{ fontSize: 14 }} />
          环境要求
        </span>
        <DownOutlined
          style={{
            fontSize: 14,
            color: colors.textSecondary,
            transition: 'transform 0.2s',
            transform: open ? 'rotate(180deg)' : 'none',
          }}
        />
      </button>
      {open && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            marginTop: 12,
            borderRadius: 16,
            border: CARD_BORDER,
            padding: 16,
          }}
        >
          {prereq && (
            <p style={{ margin: 0, fontSize: 12, lineHeight: 1.7, color: colors.textSecondary }}>
              {ENGINE_PREREQUISITES_ZH[providerId] ?? prereq}
            </p>
          )}
          {installHint && <CopyableCommand command={installHint} />}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Button
              onClick={() => void runCheck()}
              disabled={checking}
              loading={checking}
              icon={checking ? undefined : <ReloadOutlined style={{ fontSize: 14 }} />}
              style={{ fontSize: 12, fontWeight: 500, height: 'auto', padding: '6px 12px' }}
            >
              检查环境
            </Button>
            {report && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: '11.5px',
                  fontWeight: 500,
                  color: report.ok ? colors.success : colors.warning,
                }}
              >
                {report.ok ? '可以使用' : '尚不可用'}
              </span>
            )}
          </div>
          {report && (
            <ul
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                margin: 0,
                padding: 0,
                paddingTop: 12,
                borderTop: CARD_BORDER,
                listStyle: 'none',
              }}
            >
              {report.checks.map((c) => (
                <CheckRow
                  key={c.key}
                  ok={c.ok}
                  optional={c.optional}
                  label={c.label}
                  detail={c.detail}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

/* ------------------------------ Main component ---------------------------- */

export default function EngineDetail({
  provider,
  kbs,
  onBack,
  onOpenKb,
  onSelectMode,
  onChanged,
  onError,
}: EngineDetailProps) {
  const status = resolveStatus(provider);
  const Icon = ENGINE_ICONS[provider.id] ?? AppstoreOutlined;
  const installHint = INSTALL_HINTS[provider.id];
  const hasModes = (provider.modes?.length ?? 0) > 0;

  const engineKbs = useMemo(
    () => kbs.filter((kb) => kbProvider(kb) === provider.id),
    [kbs, provider.id],
  );

  return (
    <div style={{ flex: 1, overflowY: 'auto', background: colors.bgContent }}>
      <div style={{ maxWidth: 768, margin: '0 auto', padding: '32px 24px' }}>
        <Button
          type="text"
          onClick={onBack}
          icon={<ArrowLeftOutlined style={{ fontSize: 14 }} />}
          style={{
            marginBottom: 12,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            fontSize: '11.5px',
            fontWeight: 500,
            color: colors.textSecondary,
            height: 'auto',
            padding: '2px 4px',
          }}
        >
          知识中心
        </Button>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div
            style={{
              display: 'flex',
              height: 44,
              width: 44,
              flexShrink: 0,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 16,
              border: CARD_BORDER,
              color: colors.textPrimary,
            }}
          >
            <Icon style={{ fontSize: 20 }} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
              <h1
                style={{
                  margin: 0,
                  fontFamily: SERIF,
                  fontSize: 20,
                  fontWeight: 600,
                  letterSpacing: '-0.01em',
                  color: colors.textPrimary,
                }}
              >
                {provider.name}
              </h1>
              <StatusBadge status={status} />
            </div>
            <p style={{ marginTop: 4, marginBottom: 0, fontSize: '12.5px', lineHeight: 1.7, color: colors.textSecondary }}>
              {provider.description}
            </p>
          </div>
        </div>

        {/* Requirements & environment — collapsible, unified across engines.
            Auto-opens when the engine isn't ready so the gap is obvious. */}
        <EnvRequirements
          providerId={provider.id}
          installHint={installHint}
          defaultOpen={status !== 'ready'}
          onError={onError}
        />

        {/* Retrieval modes (graphrag / lightrag) */}
        {hasModes && (
          <Section label="检索模式" icon={DeploymentUnitOutlined}>
            <p style={{ marginTop: -4, marginBottom: 12, fontSize: '11.5px', lineHeight: 1.4, color: colors.textSecondary }}>
              新检索的默认模式。单个知识库仍可各自覆盖。
            </p>
            <ModeSelector provider={provider} onSelectMode={onSelectMode} />
          </Section>
        )}

        {/* LlamaIndex tuning */}
        {provider.id === 'llamaindex' && (
          <Section label="检索与分块" icon={ControlOutlined}>
            <LlamaIndexForm onChanged={onChanged} onError={onError} />
          </Section>
        )}

        {/* GraphRAG query knobs */}
        {provider.id === 'graphrag' && (
          <Section label="检索参数" icon={ControlOutlined}>
            <GraphRagForm onChanged={onChanged} onError={onError} />
          </Section>
        )}

        {/* LightRAG query knobs */}
        {provider.id === 'lightrag' && (
          <Section label="检索参数" icon={ControlOutlined}>
            <LightRagForm onChanged={onChanged} onError={onError} />
          </Section>
        )}

        {/* PageIndex credentials */}
        {provider.id === 'pageindex' && (
          <Section label="凭证" icon={KeyOutlined}>
            <PageIndexForm onChanged={onChanged} onError={onError} />
          </Section>
        )}

        {/* Models — in-place pickers for the kinds this engine needs */}
        <ModelsSection providerId={provider.id} onError={onError} />

        {/* Knowledge bases on this engine */}
        <Section label={`知识库列表 · ${engineKbs.length}`} icon={DatabaseOutlined}>
          {engineKbs.length === 0 ? (
            <div
              style={{
                borderRadius: 16,
                border: `1px dashed ${colors.border}`,
                padding: '32px 16px',
                textAlign: 'center',
                fontSize: 12,
                color: colors.textSecondary,
              }}
            >
              暂无知识库使用此引擎。
            </div>
          ) : (
            <div style={{ overflow: 'hidden', borderRadius: 16, border: CARD_BORDER }}>
              {engineKbs.map((kb, i) => {
                const docs = kbDocCount(kb);
                const ready = resolveKbStatus(kb) === 'ready';
                return (
                  <KbRow
                    key={kb.name}
                    separated={i > 0}
                    ready={ready}
                    name={kb.name}
                    docs={docs}
                    onOpen={() => onOpenKb(kb.name)}
                  />
                );
              })}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}

/** KB 行按钮（源 button 行：hover 浅底、状态圆点、名称截断、右侧文档数）。 */
function KbRow({
  separated,
  ready,
  name,
  docs,
  onOpen,
}: {
  separated: boolean;
  ready: boolean;
  name: string;
  docs: number | null;
  onOpen: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      type="button"
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex',
        width: '100%',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '10px 16px',
        textAlign: 'left',
        cursor: 'pointer',
        background: hover ? colors.bgHover : 'transparent',
        borderTop: separated ? CARD_BORDER : 'none',
        borderLeft: 'none',
        borderRight: 'none',
        borderBottom: 'none',
      }}
    >
      <div style={{ display: 'flex', minWidth: 0, alignItems: 'center', gap: 8 }}>
        <span
          style={{
            display: 'inline-block',
            height: 6,
            width: 6,
            flexShrink: 0,
            borderRadius: 999,
            background: ready ? colors.success : colors.textSecondary,
          }}
        />
        <span
          style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontSize: 13,
            fontWeight: 500,
            color: colors.textPrimary,
          }}
        >
          {name}
        </span>
      </div>
      {docs !== null && (
        <span style={{ flexShrink: 0, fontSize: 11, color: colors.textSecondary }}>
          {docs} 篇文档
        </span>
      )}
    </button>
  );
}
