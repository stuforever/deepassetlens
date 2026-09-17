/**
 * 知识中心首页总览 —— 复刻 DeepTutor web/components/knowledge/KnowledgeHome.tsx（antd 重建，1:1）。
 *
 * 区块（与源同序）：页头（标题/副标题 + 新建知识库主按钮）
 *   → 检索引擎区（引擎卡片网格 + Obsidian 入口卡）
 *   → 知识库列表区（标题 + 计数徽标 + 条件搜索框；空态 / 搜索空态 / KB 卡片网格）。
 *
 * 源码转换口径：
 *   - tailwind → antd 组件 + style 对象：grid-cols-1 sm:grid-cols-2 → Row/Col(xs=24,sm=12)；
 *     line-clamp-2 → WebkitLineClamp；rounded-2xl → borderRadius 16；max-w-4xl → 896。
 *   - hover:border-[var(--ring)] 与 group-hover:opacity → onMouseEnter/onMouseLeave 直写 style
 *     （chevron 经 [data-card-chevron] 定位），与本仓 tutor 页既有口径一致。
 *   - lucide → @ant-design/icons：Boxes→AppstoreOutlined、Cloud→CloudOutlined、Network→DeploymentUnitOutlined、
 *     Workflow→PartitionOutlined、Server→HddOutlined、FolderOpen→FolderOpenOutlined、Cpu→ThunderboltOutlined、
 *     Database→DatabaseOutlined、Plus→PlusOutlined、Search→SearchOutlined、Star→StarFilled、
 *     Check→CheckOutlined、ChevronRight→RightOutlined。
 *   - 徽标/状态点 → antd Tag/Badge：就绪=success 绿 / 需配置密钥=warning 橙 / 未安装=muted；
 *     状态点 live 态用 Badge processing 自带呼吸动画（替代源 animate-pulse）。
 *   - t('English') → 中文直出（对照 dt_baseline/fieldlists/knowledge.md §4 与 web/locales/zh/app.json）。
 *   - B0 增量：KB 卡标题区状态点之后追加 tutor 域紫徽标（源码无此元素）。
 */
import { useMemo, useState } from "react";
import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";
import { Badge, Button, Col, Input, Row, Tag } from "antd";
import {
  AppstoreOutlined,
  CheckOutlined,
  CloudOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  FolderOpenOutlined,
  HddOutlined,
  PartitionOutlined,
  PlusOutlined,
  RightOutlined,
  SearchOutlined,
  StarFilled,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  kbDocCount,
  kbHasLiveProgress,
  kbNeedsReindex,
  kbProvider,
  resolveKbStatus,
  type KnowledgeBase,
} from "./knowledge-helpers";
import type { RagProviderSummary } from "./knowledge-api";
import { tokens } from "../../theme/tokens";

interface KnowledgeHomeProps {
  kbs: KnowledgeBase[];
  providers: RagProviderSummary[];
  onOpenKb: (name: string) => void;
  onOpenEngine: (id: string) => void;
  onCreate: () => void;
  /** Open the create flow pre-set to link an Obsidian vault. */
  onConnectObsidian: () => void;
}

const ENGINE_ICONS: Record<string, typeof AppstoreOutlined> = {
  llamaindex: AppstoreOutlined,
  pageindex: CloudOutlined,
  graphrag: DeploymentUnitOutlined,
  lightrag: PartitionOutlined,
  "lightrag-server": HddOutlined,
};

type EngineStatus = "ready" | "needs_key" | "unavailable";

function engineStatus(p: RagProviderSummary): EngineStatus {
  if (p.requires_api_key && p.configured === false) return "needs_key";
  if (p.configured === false) return "unavailable";
  return "ready";
}

/* ---------- 样式常量（tailwind 类 → style 对象） ---------- */

const BADGE_PILL: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  fontSize: 10,
  fontWeight: 500,
  lineHeight: "14px",
  paddingBlock: 2,
  paddingInline: 6,
  borderRadius: tokens.radius.pill,
  marginInlineEnd: 0,
};

const SECTION_TITLE: CSSProperties = {
  margin: 0,
  display: "flex",
  alignItems: "center",
  gap: 8,
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: "0.025em",
  textTransform: "uppercase",
  color: tokens.colors.textSecondary,
};

const COUNT_CHIP: CSSProperties = {
  borderRadius: tokens.radius.pill,
  background: tokens.colors.bgSubtle,
  color: tokens.colors.textSecondary,
  padding: "2px 6px",
  fontSize: 10,
  fontWeight: 400,
};

const CARD: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 8,
  width: "100%",
  height: "100%",
  textAlign: "left",
  borderRadius: 16,
  border: `1px solid ${tokens.colors.border}`,
  background: tokens.colors.bgContent,
  color: "inherit",
  font: "inherit",
  cursor: "pointer",
  transition: "border-color 200ms",
};

const CARD_TITLE_ROW: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 8,
};

const CARD_TITLE_NAME: CSSProperties = {
  overflow: "hidden",
  whiteSpace: "nowrap",
  textOverflow: "ellipsis",
  fontSize: 13.5,
  fontWeight: 500,
  color: tokens.colors.textPrimary,
};

const CARD_DESC: CSSProperties = {
  margin: 0,
  fontSize: 11.5,
  lineHeight: 1.375,
  color: tokens.colors.textSecondary,
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

const CARD_FOOTER: CSSProperties = {
  marginTop: "auto",
  display: "flex",
  alignItems: "center",
  gap: 8,
  paddingTop: 4,
  fontSize: 11,
  color: tokens.colors.textSecondary,
};

const MINI_CHIP: CSSProperties = {
  borderRadius: tokens.radius.pill,
  border: `1px solid ${tokens.colors.border}`,
  padding: "2px 6px",
};

const CARD_CHEVRON: CSSProperties = {
  marginLeft: "auto",
  fontSize: 14,
  color: tokens.colors.textSecondary,
  opacity: 0,
  transition: "opacity 200ms",
};

const CREATE_BTN: CSSProperties = {
  flexShrink: 0,
  display: "inline-flex",
  alignItems: "center",
  height: "auto",
  padding: "8px 14px",
  fontSize: 12.5,
  fontWeight: 500,
  borderRadius: 8,
};

/** hover:border-[var(--ring)] + group-hover chevron → 内联事件直写（本仓既定口径）。 */
const cardHover = {
  onMouseEnter: (e: ReactMouseEvent<HTMLElement>) => {
    e.currentTarget.style.borderColor = tokens.colors.primary;
    const chevron = e.currentTarget.querySelector<HTMLElement>("[data-card-chevron]");
    if (chevron) chevron.style.opacity = "0.6";
  },
  onMouseLeave: (e: ReactMouseEvent<HTMLElement>) => {
    e.currentTarget.style.borderColor = tokens.colors.border;
    const chevron = e.currentTarget.querySelector<HTMLElement>("[data-card-chevron]");
    if (chevron) chevron.style.opacity = "0";
  },
};

/* ---------- 文件内子组件（与源同构） ---------- */

function EngineStatusBadge({ status }: { status: EngineStatus }) {
  if (status === "ready") {
    return (
      <Tag color="success" style={BADGE_PILL}>
        <CheckOutlined style={{ fontSize: 12 }} />
        就绪
      </Tag>
    );
  }
  if (status === "needs_key") {
    return (
      <Tag color="warning" style={BADGE_PILL}>
        需配置密钥
      </Tag>
    );
  }
  return (
    <Tag
      style={{
        ...BADGE_PILL,
        background: tokens.colors.bgSubtle,
        color: tokens.colors.textSecondary,
        borderColor: "transparent",
      }}
    >
      未安装
    </Tag>
  );
}

function StatusDot({ kb }: { kb: KnowledgeBase }) {
  const status = resolveKbStatus(kb);
  const needsReindex = kbNeedsReindex(kb);
  const isLive = kbHasLiveProgress(kb);
  const dotStatus = needsReindex
    ? "warning"
    : status === "error"
      ? "error"
      : isLive
        ? "processing"
        : status === "ready"
          ? "success"
          : "default";
  return <Badge status={dotStatus} styles={{ indicator: { width: 8, height: 8 } }} />;
}

export default function KnowledgeHome({
  kbs,
  providers,
  onOpenKb,
  onOpenEngine,
  onCreate,
  onConnectObsidian,
}: KnowledgeHomeProps) {
  const [query, setQuery] = useState("");
  const providerName = (id: string) =>
    providers.find((p) => p.id === id)?.name ??
    id.charAt(0).toUpperCase() + id.slice(1);

  const obsidianCount = useMemo(
    () => kbs.filter((kb) => kb.metadata?.type === "obsidian").length,
    [kbs],
  );
  const kbCountByProvider = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const kb of kbs)
      counts[kbProvider(kb)] = (counts[kbProvider(kb)] ?? 0) + 1;
    return counts;
  }, [kbs]);

  const filteredKbs = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return kbs;
    return kbs.filter((kb) => kb.name.toLowerCase().includes(q));
  }, [kbs, query]);

  return (
    <div style={{ flex: 1, overflowY: "auto", background: tokens.colors.bgContent }}>
      <div style={{ maxWidth: 896, margin: "0 auto", padding: "32px 24px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 19, fontWeight: 600, letterSpacing: "-0.025em", color: tokens.colors.textPrimary }}>
              知识中心
            </h1>
            <p style={{ margin: "4px 0 0", fontSize: 12.5, color: tokens.colors.textSecondary }}>
              管理你的知识库与检索引擎。
            </p>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined style={{ fontSize: 14 }} />}
            onClick={onCreate}
            style={CREATE_BTN}
          >
            新建知识库
          </Button>
        </div>

        {/* Retrieval engines */}
        <section style={{ marginTop: 32 }}>
          <h2 style={{ ...SECTION_TITLE, marginBottom: 12 }}>
            <ThunderboltOutlined style={{ fontSize: 14 }} />
            检索引擎
          </h2>
          <Row gutter={[12, 12]}>
            {providers.map((p) => {
              const status = engineStatus(p);
              const Icon = ENGINE_ICONS[p.id] ?? AppstoreOutlined;
              const count = kbCountByProvider[p.id] ?? 0;
              return (
                <Col xs={24} sm={12} key={p.id}>
                  <button
                    type="button"
                    onClick={() => onOpenEngine(p.id)}
                    style={{ ...CARD, padding: 14 }}
                    {...cardHover}
                  >
                    <div style={CARD_TITLE_ROW}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                        <Icon style={{ fontSize: 16, flexShrink: 0, color: tokens.colors.textSecondary }} />
                        <span style={CARD_TITLE_NAME}>{p.name}</span>
                      </div>
                      <EngineStatusBadge status={status} />
                    </div>
                    <p style={CARD_DESC}>{p.description}</p>
                    <div style={CARD_FOOTER}>
                      {p.modes && p.modes.length > 0 && p.default_mode && (
                        <span style={{ ...MINI_CHIP, fontFamily: "Consolas, Menlo, monospace" }}>
                          {p.default_mode}
                        </span>
                      )}
                      {count > 0 && <span>{count} 个知识库</span>}
                      <RightOutlined data-card-chevron style={CARD_CHEVRON} />
                    </div>
                  </button>
                </Col>
              );
            })}

            {/* Obsidian — a connected source, not a config-backed engine: a
                pointer to a live vault the tutor reads & writes in place. Shown
                here for discoverability; clicking opens the unified create flow
                pre-set to link a vault. */}
            <Col xs={24} sm={12}>
              <button
                type="button"
                onClick={onConnectObsidian}
                style={{ ...CARD, padding: 14 }}
                {...cardHover}
              >
                <div style={CARD_TITLE_ROW}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                    <FolderOpenOutlined style={{ fontSize: 16, flexShrink: 0, color: tokens.colors.textSecondary }} />
                    <span style={CARD_TITLE_NAME}>Obsidian</span>
                  </div>
                  {obsidianCount > 0 && (
                    <Tag color="success" style={BADGE_PILL}>
                      <CheckOutlined style={{ fontSize: 12 }} />
                      已连接 {obsidianCount} 个
                    </Tag>
                  )}
                </div>
                <p style={CARD_DESC}>
                  连接你的 Obsidian 库。导师直接在原文件上浏览并写入笔记——不上传、不索引。仅限本地 / 自托管。
                </p>
                <div style={CARD_FOOTER}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <FolderOpenOutlined style={{ fontSize: 12 }} />
                    连接 Vault
                  </span>
                  <RightOutlined data-card-chevron style={CARD_CHEVRON} />
                </div>
              </button>
            </Col>
          </Row>
        </section>

        {/* Knowledge bases */}
        <section style={{ marginTop: 32, paddingBottom: 8 }}>
          <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
            <h2 style={SECTION_TITLE}>
              <DatabaseOutlined style={{ fontSize: 14 }} />
              知识库列表
              <span style={COUNT_CHIP}>{kbs.length}</span>
            </h2>
            {kbs.length > 6 && (
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索知识库…"
                prefix={<SearchOutlined style={{ color: tokens.colors.textSecondary, fontSize: 14 }} />}
                style={{ width: 192, fontSize: 12, borderRadius: 8 }}
              />
            )}
          </div>

          {kbs.length === 0 ? (
            <div
              style={{
                borderRadius: 16,
                border: `1px dashed ${tokens.colors.border}`,
                padding: "48px 16px",
                textAlign: "center",
              }}
            >
              <DatabaseOutlined style={{ fontSize: 24, color: tokens.colors.textSecondary, marginBottom: 8 }} />
              <div style={{ fontSize: 13, fontWeight: 500, color: tokens.colors.textPrimary }}>暂无知识库</div>
              <p style={{ margin: "4px auto 0", maxWidth: 384, fontSize: 12, lineHeight: 1.625, color: tokens.colors.textSecondary }}>
                创建一个知识库，上传文档，在对话中检索有依据的内容。
              </p>
              <Button
                type="primary"
                icon={<PlusOutlined style={{ fontSize: 14 }} />}
                onClick={onCreate}
                style={{ ...CREATE_BTN, marginTop: 16 }}
              >
                新建知识库
              </Button>
            </div>
          ) : filteredKbs.length === 0 ? (
            <div
              style={{
                borderRadius: 16,
                border: `1px dashed ${tokens.colors.border}`,
                padding: "32px 16px",
                textAlign: "center",
                fontSize: 12,
                color: tokens.colors.textSecondary,
              }}
            >
              未找到匹配项
            </div>
          ) : (
            <Row gutter={[12, 12]}>
              {filteredKbs.map((kb) => {
                const docs = kbDocCount(kb);
                return (
                  <Col xs={24} sm={12} key={kb.name}>
                    <button
                      type="button"
                      onClick={() => onOpenKb(kb.name)}
                      style={{ ...CARD, padding: 16 }}
                      {...cardHover}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <StatusDot kb={kb} />
                        {(kb as any).rag_provider === "tutor_dt" && <Tag color="purple">tutor 域</Tag>}
                        <span style={CARD_TITLE_NAME}>{kb.name}</span>
                        {kb.is_default && (
                          <StarFilled style={{ fontSize: 12, flexShrink: 0, color: tokens.colors.warning }} />
                        )}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: tokens.colors.textSecondary }}>
                        <span style={MINI_CHIP}>{providerName(kbProvider(kb))}</span>
                        {docs !== null && <span>{docs} 篇文档</span>}
                      </div>
                    </button>
                  </Col>
                );
              })}
            </Row>
          )}
        </section>
      </div>
    </div>
  );
}
