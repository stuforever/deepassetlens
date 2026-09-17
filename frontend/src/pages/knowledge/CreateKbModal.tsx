/**
 * 复刻自 DeepTutor 原仓 web/components/knowledge/CreateKbModal.tsx（918 行，整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. @/components/common/Modal → antd Modal（open/onCancel 受控语义等价；submitting 时
 *    closable/maskClosable/keyboard 全关 + footer 取消钮禁用，对应源 closeOnBackdrop/
 *    closeOnEscape/onClose=noop；width "lg"→600px，titleIcon=Plus 并入 title）；
 * 3. lucide → @ant-design/icons：Plus→PlusOutlined、Link2→LinkOutlined、Check→CheckOutlined、
 *    AlertTriangle→WarningOutlined、Loader2→Button loading（图标自动让位 spinner）、
 *    FolderSearch→FolderOpenOutlined、Server→CloudServerOutlined、FolderOpen→FolderOpenOutlined；
 * 4. Tailwind → antd theme.useToken() + 内联样式（amber/red/emerald 调色板 hex 直用；
 *    选中卡片 = 描边 colorPrimary + 底色 colorPrimaryBg；卡片 hover 描边经 onMouseEnter/
 *    Leave 直写 style，沿批8 最小等价物先例）；
 * 5. t() 译文按 backend/scripts/dt_baseline/fieldlists/knowledge.md §2 内联中文；zh 未收录键
 *    "This engine isn't installed on the server. Install it before creating." 保留英文原文；
 *    EXAMPLE_SERVER_URL / EXAMPLE_VAULT_PATH / EXAMPLE_INDEX_PATH 为字面量 placeholder 原样保留；
 * 6. validateFiles 按名 import './knowledge-helpers'（并行批件，逐函数移植），t 契约 →
 *    本文件 zhT()（与 KbDocumentsSection 同款：键=英文原文，映射对拍 zh/app.json）；
 *    probeLinkedFolder / probeLightRagServer 与类型 RagProviderSummary /
 *    KnowledgeUploadPolicy / LinkedFolderProbe / LightRagServerProbe 按名 import ./knowledge-api
 *    （数据层由并行批件提供，勿在此造）。
 *
 * 模式/字段分支（与源一致）：
 * - ModeToggle 双卡片：新建（上传文档建索引）/ 关联已有（就地挂载已有索引）；
 * - 新建模式 NewModeFields：索引引擎卡片单选（needs_key=「需配置密钥」amber 徽标 /
 *   unavailable=「未安装」muted 徽标 + 不可用提示条 + 配置入口）→ provider=lightrag-server 时
 *   LightRagServerFields 连接表单（服务器地址 + 测试连接 probe、API key·可选、检索模式 Select）
 *   替换 FileDropZone 上传区且提交前须 probe.ok；其余引擎走「初始文档」FileDropZone
 *   （pageindex 用 PAGEINDEX_FORMATS 覆盖上传策略）且须有有效文件；
 * - 关联模式 LinkModeFields：来源卡片单选（linkable=false 禁用=「云端索引」徽标 + title 说明，
 *   另有 Obsidian 卡片）→ 路径输入（obsidian=Vault 路径、路径非空即可提交；引擎索引=文件夹
 *   路径 + 「检查文件夹」probe、probe.ok 才可提交）+ ProbeVerdict 结果面板；
 * - 提交按钮文案随模式：新建+普通引擎=创建 / 新建+lightrag-server=连接 / 关联+obsidian=连接 /
 *   关联+其他=链接；
 * - 打开（closed→open）时重置表单（防后台轮询清空输入）；folderPath/linkSource 变化清 probe；
 *   serverUrl/apiKey 变化清 serverProbe。
 */
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import {
  CheckOutlined,
  CloudServerOutlined,
  FolderOpenOutlined,
  LinkOutlined,
  PlusOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Alert, Button, Input, Modal, Select, theme } from "antd";
import {
  probeLightRagServer,
  probeLinkedFolder,
  type KnowledgeUploadPolicy,
  type LightRagServerProbe,
  type LinkedFolderProbe,
  type RagProviderSummary,
} from "./knowledge-api";
import FileDropZone from "./FileDropZone";
import { validateFiles } from "./knowledge-helpers";

/** validateFiles 的 t 契约：键=英文原文，中文映射对拍 zh/app.json；模板插值 {{var}} 本地替换。 */
const ZH: Record<string, string> = {
  "Unsupported file type": "不支持的文件类型",
  "This file exceeds the maximum size of {{size}}.":
    "该文件超过了 {{size}} 的大小限制。",
  "No extension": "无扩展名",
};

const zhT = (key: string, vars?: Record<string, unknown>): string => {
  let text = ZH[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replace(new RegExp(`{{\\s*${name}\\s*}}`, "g"), String(value));
    }
  }
  return text;
};

// Mirrors SUPPORTED_EXTENSIONS in the backend pageindex pipeline (PageIndex POST /doc/).
const PAGEINDEX_FORMATS = [
  ".pdf",
  ".md",
  ".markdown",
  ".txt",
  ".docx",
  ".doc",
  ".pptx",
  ".ppt",
  ".xlsx",
  ".xls",
  ".csv",
];
const OBSIDIAN_SOURCE = "obsidian";
const LIGHTRAG_SERVER_PROVIDER = "lightrag-server";
const EXAMPLE_INDEX_PATH = "/Users/you/knowledge_bases/my-kb";
const EXAMPLE_VAULT_PATH = "/Users/you/Documents/MyVault";
const EXAMPLE_SERVER_URL = "http://localhost:9621";

type Mode = "new" | "link";

interface CreateKbModalProps {
  isOpen: boolean;
  onClose: () => void;
  providers: RagProviderSummary[];
  uploadPolicy: KnowledgeUploadPolicy;
  onCreate: (params: {
    name: string;
    provider: string;
    files: File[];
  }) => Promise<void>;
  /** Link a pre-built engine index folder in place (no copy, no re-index). */
  onConnectLinkedFolder: (params: {
    name: string;
    folderPath: string;
    provider: string;
  }) => Promise<void>;
  /** Connect a live Obsidian vault (no index). */
  onConnectObsidian: (params: {
    name: string;
    vaultPath: string;
  }) => Promise<void>;
  /** Connect an external LightRAG server (retrieval only, no local index). */
  onConnectLightRagServer: (params: {
    name: string;
    serverUrl: string;
    apiKey?: string;
    mode?: string;
  }) => Promise<void>;
  /** Open the RAG pipeline settings (to add a missing API key). */
  onConfigureProvider?: () => void;
  /** Open straight into a given mode (e.g. "link" from the Obsidian card). */
  initialMode?: Mode;
  /** Pre-select a link source (engine id or "obsidian") when opening in link mode. */
  initialSource?: string;
}

type AntdToken = ReturnType<typeof theme.useToken>["token"];

// Tailwind 调色板 hex 对位（light 模式取值，本文件局部用）。
const AMBER_BADGE_BG = "#fef3c7"; // amber-100
const AMBER_BADGE_TEXT = "#b45309"; // amber-700
const AMBER_ALERT_BORDER = "#fde68a"; // amber-200
const AMBER_ALERT_BG = "#fffbeb"; // amber-50
const AMBER_ALERT_TEXT = "#92400e"; // amber-800
const RED_ERROR_BORDER = "#fecaca"; // red-200
const RED_ERROR_BG = "#fef2f2"; // red-50
const RED_ERROR_TEXT = "#b91c1c"; // red-700
const EMERALD_TEXT = "#047857"; // emerald-700
const MONO_FONT =
  "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace";

/** 源 label 样式：11px 中字重 + 大写 + 宽字距（对中文为 no-op，样式语义保留）。 */
const labelStyle = (token: AntdToken): CSSProperties => ({
  display: "block",
  marginBottom: 4,
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: "0.025em",
  textTransform: "uppercase",
  color: token.colorTextSecondary,
});

/** 卡片单选钮（ModeToggle / 引擎选择 / 来源选择共用）：hover 描边经 onMouseEnter/Leave 直写。 */
function SelectCard({
  selected,
  disabled,
  onClick,
  title,
  children,
}: {
  selected: boolean;
  disabled: boolean;
  onClick: () => void;
  title?: string;
  children: ReactNode;
}) {
  const { token } = theme.useToken();
  const [hovered, setHovered] = useState(false);
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        borderRadius: 16,
        border: "1px solid",
        padding: 12,
        textAlign: "left",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        borderColor: selected
          ? token.colorPrimary
          : hovered && !disabled
            ? token.colorPrimaryHover
            : token.colorBorder,
        background: selected ? token.colorPrimaryBg : "transparent",
        transition: "border-color 0.2s ease, background 0.2s ease",
        fontFamily: "inherit",
      }}
    >
      {children}
    </button>
  );
}

/** muted 底小徽标（未安装 / 云端索引）。 */
function MutedBadge({ token, text }: { token: AntdToken; text: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        borderRadius: 999,
        background: token.colorFillQuaternary,
        padding: "2px 6px",
        fontSize: 10,
        fontWeight: 500,
        color: token.colorTextSecondary,
      }}
    >
      {text}
    </span>
  );
}

/** amber 底小徽标（需配置密钥）。 */
function AmberBadge({ text }: { text: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        borderRadius: 999,
        background: AMBER_BADGE_BG,
        padding: "2px 6px",
        fontSize: 10,
        fontWeight: 500,
        color: AMBER_BADGE_TEXT,
      }}
    >
      {text}
    </span>
  );
}

/** 红色错误框（pre 等宽换行，保留源错误文本格式）。 */
function ErrorBox({ error, token }: { error: string; token: AntdToken }) {
  return (
    <div
      style={{
        borderRadius: 8,
        border: `1px solid ${RED_ERROR_BORDER}`,
        background: RED_ERROR_BG,
        padding: "8px 12px",
        fontSize: 12,
        color: RED_ERROR_TEXT,
      }}
    >
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
          fontFamily: MONO_FONT,
          fontSize: 11,
          lineHeight: 1.6,
        }}
      >
        {error}
      </pre>
    </div>
  );
}

export default function CreateKbModal({
  isOpen,
  onClose,
  providers,
  uploadPolicy,
  onCreate,
  onConnectLinkedFolder,
  onConnectObsidian,
  onConnectLightRagServer,
  onConfigureProvider,
  initialMode = "new",
  initialSource,
}: CreateKbModalProps) {
  const { token } = theme.useToken();
  const [mode, setMode] = useState<Mode>("new");
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("llamaindex");
  const [files, setFiles] = useState<File[]>([]);
  // Link mode: the source is either an engine id or the Obsidian sentinel.
  const [linkSource, setLinkSource] = useState(OBSIDIAN_SOURCE);
  const [folderPath, setFolderPath] = useState("");
  const [probe, setProbe] = useState<LinkedFolderProbe | null>(null);
  const [probing, setProbing] = useState(false);
  // LightRAG Server engine (new mode): a connection instead of an upload.
  const [serverUrl, setServerUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [serverMode, setServerMode] = useState("");
  const [serverProbe, setServerProbe] = useState<LightRagServerProbe | null>(
    null,
  );
  const [serverProbing, setServerProbing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const firstLinkable = providers.find((p) => p.linkable)?.id;

  // Reset the form only on the closed → open transition. While the modal is
  // open, background indexing polls replace `providers` (and friends) every
  // few seconds, and a data refresh must never wipe user input (#691).
  const wasOpenRef = useRef(false);
  useEffect(() => {
    const justOpened = isOpen && !wasOpenRef.current;
    wasOpenRef.current = isOpen;
    if (!justOpened) return;
    setMode(initialMode);
    setName("");
    setFiles([]);
    setError(null);
    setProvider(initialSource || providers[0]?.id || "llamaindex");
    setLinkSource(initialSource || firstLinkable || OBSIDIAN_SOURCE);
    setFolderPath("");
    setProbe(null);
    setProbing(false);
    setServerUrl("");
    setApiKey("");
    setServerMode("");
    setServerProbe(null);
    setServerProbing(false);
  }, [isOpen, providers, firstLinkable, initialMode, initialSource]);

  // A fresh path / source invalidates a stale probe verdict.
  useEffect(() => {
    setProbe(null);
  }, [folderPath, linkSource]);

  // A fresh URL / key invalidates a stale server connection test.
  useEffect(() => {
    setServerProbe(null);
  }, [serverUrl, apiKey]);

  // ---- New mode (build a fresh index) ----------------------------------
  const activeProvider = providers.find((p) => p.id === provider);
  const providerNeedsKey =
    !!activeProvider?.requires_api_key && activeProvider?.configured === false;
  const providerUnavailable = activeProvider?.configured === false;
  const isPageIndex = provider === "pageindex";
  const isLightRagServer = provider === LIGHTRAG_SERVER_PROVIDER;
  const serverModeOptions = activeProvider?.modes ?? [];
  const effectiveServerMode =
    serverMode || activeProvider?.default_mode || serverModeOptions[0] || "";

  const policyForProvider: KnowledgeUploadPolicy = isPageIndex
    ? {
        ...uploadPolicy,
        extensions: PAGEINDEX_FORMATS,
        accept: PAGEINDEX_FORMATS.join(","),
      }
    : uploadPolicy;

  const selection = validateFiles(files, policyForProvider, zhT);

  // ---- Link mode (mount an existing folder) ----------------------------
  const linkIsObsidian = linkSource === OBSIDIAN_SOURCE;
  const trimmed = name.trim();
  const trimmedPath = folderPath.trim();

  const trimmedServerUrl = serverUrl.trim();

  const canSubmit = (() => {
    if (submitting) return false;
    if (!trimmed) return false;
    if (mode === "new") {
      if (isLightRagServer) {
        // The connection must pass the test before a KB is bound to it.
        return !!trimmedServerUrl && !!serverProbe?.ok;
      }
      return !providerUnavailable && selection.validFiles.length > 0;
    }
    if (!trimmedPath) return false;
    if (linkIsObsidian) return true;
    // An engine index must pass the probe before it can be linked.
    return !!probe?.ok;
  })();

  const handleProbe = async () => {
    if (!trimmedPath || linkIsObsidian || probing) return;
    setProbing(true);
    setError(null);
    try {
      const result = await probeLinkedFolder({
        folderPath: trimmedPath,
        provider: linkSource,
      });
      setProbe(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setProbing(false);
    }
  };

  const handleTestServer = async () => {
    if (!trimmedServerUrl || serverProbing) return;
    setServerProbing(true);
    setError(null);
    try {
      const result = await probeLightRagServer({
        serverUrl: trimmedServerUrl,
        apiKey: apiKey.trim(),
      });
      setServerProbe(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setServerProbing(false);
    }
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "new") {
        if (isLightRagServer) {
          await onConnectLightRagServer({
            name: trimmed,
            serverUrl: trimmedServerUrl,
            apiKey: apiKey.trim(),
            mode: effectiveServerMode,
          });
        } else {
          await onCreate({
            name: trimmed,
            provider,
            files: selection.validFiles,
          });
        }
      } else if (linkIsObsidian) {
        await onConnectObsidian({ name: trimmed, vaultPath: trimmedPath });
      } else {
        await onConnectLinkedFolder({
          name: trimmed,
          folderPath: trimmedPath,
          provider: linkSource,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const submitLabel =
    mode === "new"
      ? isLightRagServer
        ? "连接"
        : "创建"
      : linkIsObsidian
        ? "连接"
        : "链接";

  return (
    <Modal
      open={isOpen}
      onCancel={onClose}
      title={
        <span
          style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
        >
          <PlusOutlined style={{ fontSize: 14 }} />
          创建知识库
        </span>
      }
      width={600}
      closable={!submitting}
      maskClosable={!submitting}
      keyboard={!submitting}
      footer={
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 8,
          }}
        >
          <Button type="text" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button
            type="primary"
            onClick={() => void handleSubmit()}
            disabled={!canSubmit}
            loading={submitting}
            icon={
              mode === "new" && !isLightRagServer ? (
                <PlusOutlined />
              ) : (
                <LinkOutlined />
              )
            }
          >
            {submitLabel}
          </Button>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* New vs. link existing */}
        <ModeToggle mode={mode} onChange={setMode} disabled={submitting} />

        <div>
          <label style={labelStyle(token)}>知识库名称</label>
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoFocus
            disabled={submitting}
            placeholder="例如：project-papers"
            style={{ fontSize: 13 }}
          />
        </div>

        {mode === "new" ? (
          <NewModeFields
            providers={providers}
            provider={provider}
            setProvider={setProvider}
            submitting={submitting}
            providerUnavailable={providerUnavailable}
            providerNeedsKey={providerNeedsKey}
            onConfigureProvider={onConfigureProvider}
            isPageIndex={isPageIndex}
            files={files}
            setFiles={setFiles}
            policyForProvider={policyForProvider}
            connectionForm={
              isLightRagServer ? (
                <LightRagServerFields
                  serverUrl={serverUrl}
                  setServerUrl={setServerUrl}
                  apiKey={apiKey}
                  setApiKey={setApiKey}
                  serverMode={effectiveServerMode}
                  setServerMode={setServerMode}
                  modeOptions={serverModeOptions}
                  submitting={submitting}
                  probing={serverProbing}
                  probe={serverProbe}
                  onTest={handleTestServer}
                />
              ) : null
            }
          />
        ) : (
          <LinkModeFields
            providers={providers}
            linkSource={linkSource}
            setLinkSource={setLinkSource}
            linkIsObsidian={linkIsObsidian}
            folderPath={folderPath}
            setFolderPath={setFolderPath}
            submitting={submitting}
            probing={probing}
            probe={probe}
            onProbe={handleProbe}
          />
        )}

        {error && <ErrorBox error={error} token={token} />}
      </div>
    </Modal>
  );
}

function ModeToggle({
  mode,
  onChange,
  disabled,
}: {
  mode: Mode;
  onChange: (mode: Mode) => void;
  disabled: boolean;
}) {
  const { token } = theme.useToken();
  const options: {
    id: Mode;
    label: string;
    hint: string;
    icon: typeof PlusOutlined;
  }[] = [
    {
      id: "new",
      label: "新建",
      hint: "上传文档并建立全新索引。",
      icon: PlusOutlined,
    },
    {
      id: "link",
      label: "关联已有",
      hint: "复用你已建好的索引——就地读取，不上传、不重新索引。",
      icon: LinkOutlined,
    },
  ];
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
        gap: 8,
      }}
    >
      {options.map((opt) => {
        const selected = mode === opt.id;
        const Icon = opt.icon;
        return (
          <SelectCard
            key={opt.id}
            selected={selected}
            disabled={disabled}
            onClick={() => onChange(opt.id)}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 500,
                color: token.colorText,
              }}
            >
              <Icon style={{ fontSize: 14 }} />
              {opt.label}
            </span>
            <span
              style={{
                fontSize: 11,
                lineHeight: 1.4,
                color: token.colorTextSecondary,
              }}
            >
              {opt.hint}
            </span>
          </SelectCard>
        );
      })}
    </div>
  );
}

function NewModeFields({
  providers,
  provider,
  setProvider,
  submitting,
  providerUnavailable,
  providerNeedsKey,
  onConfigureProvider,
  isPageIndex,
  files,
  setFiles,
  policyForProvider,
  connectionForm,
}: {
  providers: RagProviderSummary[];
  provider: string;
  setProvider: (id: string) => void;
  submitting: boolean;
  providerUnavailable: boolean;
  providerNeedsKey: boolean;
  onConfigureProvider?: () => void;
  isPageIndex: boolean;
  files: File[];
  setFiles: (files: File[]) => void;
  policyForProvider: KnowledgeUploadPolicy;
  /** When set, replaces the upload step (e.g. a server connection form). */
  connectionForm?: ReactNode;
}) {
  const { token } = theme.useToken();
  return (
    <>
      <div>
        <label style={labelStyle(token)}>索引引擎</label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 8,
          }}
        >
          {providers.map((p) => {
            const selected = provider === p.id;
            const needsKey = !!p.requires_api_key && p.configured === false;
            const unavailable = p.configured === false && !p.requires_api_key;
            return (
              <SelectCard
                key={p.id}
                selected={selected}
                disabled={submitting}
                onClick={() => setProvider(p.id)}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: token.colorText,
                    }}
                  >
                    {p.name}
                  </span>
                  {needsKey ? (
                    <AmberBadge text="需配置密钥" />
                  ) : unavailable ? (
                    <MutedBadge token={token} text="未安装" />
                  ) : selected ? (
                    <CheckOutlined
                      style={{ fontSize: 14, color: token.colorPrimary }}
                    />
                  ) : null}
                </div>
                <span
                  style={{
                    fontSize: 11.5,
                    lineHeight: 1.4,
                    color: token.colorTextSecondary,
                  }}
                >
                  {p.description}
                </span>
              </SelectCard>
            );
          })}
        </div>
        {providerUnavailable && (
          <Alert
            type="warning"
            showIcon
            icon={<WarningOutlined style={{ fontSize: 14 }} />}
            style={{
              marginTop: 8,
              fontSize: 12,
              border: `1px solid ${AMBER_ALERT_BORDER}`,
              background: AMBER_ALERT_BG,
              color: AMBER_ALERT_TEXT,
            }}
            message={
              providerNeedsKey
                ? "该引擎需要 API 密钥，请先配置再创建。"
                : // zh 未收录键：运行时回退英文，复刻按原文保留。
                  "This engine isn't installed on the server. Install it before creating."
            }
            action={
              providerNeedsKey && onConfigureProvider ? (
                <Button
                  type="text"
                  size="small"
                  onClick={onConfigureProvider}
                  style={{
                    fontSize: 11.5,
                    fontWeight: 500,
                    color: AMBER_ALERT_TEXT,
                    textDecoration: "underline",
                    textUnderlineOffset: 2,
                  }}
                >
                  配置
                </Button>
              ) : undefined
            }
          />
        )}
      </div>

      {connectionForm ?? (
        <div>
          <label style={labelStyle(token)}>
            初始文档
            {isPageIndex && (
              <span
                style={{
                  marginLeft: 8,
                  textTransform: "none",
                  letterSpacing: "normal",
                  color: token.colorTextSecondary,
                }}
              >
                · 支持 PDF、Office、文本和 Markdown
              </span>
            )}
          </label>
          <FileDropZone
            files={files}
            onChange={setFiles}
            uploadPolicy={policyForProvider}
            disabled={submitting}
          />
        </div>
      )}
    </>
  );
}

function LightRagServerFields({
  serverUrl,
  setServerUrl,
  apiKey,
  setApiKey,
  serverMode,
  setServerMode,
  modeOptions,
  submitting,
  probing,
  probe,
  onTest,
}: {
  serverUrl: string;
  setServerUrl: (value: string) => void;
  apiKey: string;
  setApiKey: (value: string) => void;
  serverMode: string;
  setServerMode: (value: string) => void;
  modeOptions: string[];
  submitting: boolean;
  probing: boolean;
  probe: LightRagServerProbe | null;
  onTest: () => void;
}) {
  const { token } = theme.useToken();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <label style={labelStyle(token)}>服务器地址</label>
        <div style={{ display: "flex", gap: 8 }}>
          <Input
            value={serverUrl}
            onChange={(event) => setServerUrl(event.target.value)}
            disabled={submitting}
            placeholder={EXAMPLE_SERVER_URL}
            style={{ fontFamily: MONO_FONT, fontSize: 12.5 }}
          />
          <Button
            onClick={onTest}
            disabled={submitting || probing || serverUrl.trim().length === 0}
            loading={probing}
            icon={<CloudServerOutlined />}
            style={{ flexShrink: 0, fontSize: 12 }}
          >
            测试连接
          </Button>
        </div>
        <p
          style={{
            margin: "4px 0 0",
            fontSize: 11,
            color: token.colorTextSecondary,
          }}
        >
          {
            "你正在运行的 LightRAG 服务器的基础地址。文档在该服务器上建立索引——不会上传或复制任何内容。"
          }
        </p>
      </div>

      <div>
        <label style={labelStyle(token)}>
          {"API key"}
          <span
            style={{
              marginLeft: 8,
              textTransform: "none",
              letterSpacing: "normal",
              color: token.colorTextSecondary,
            }}
          >
            · 可选
          </span>
        </label>
        <Input.Password
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          disabled={submitting}
          autoComplete="off"
          placeholder="仅当你的服务器需要时填写"
          style={{ fontSize: 12.5 }}
        />
      </div>

      {modeOptions.length > 0 && (
        <div>
          <label style={labelStyle(token)}>检索模式</label>
          <Select
            value={serverMode}
            onChange={setServerMode}
            disabled={submitting}
            style={{ width: "100%", fontSize: 12.5 }}
            options={modeOptions.map((m) => ({ value: m, label: m }))}
          />
        </div>
      )}

      {probe && <ServerProbeVerdict probe={probe} />}
    </div>
  );
}

function ServerProbeVerdict({ probe }: { probe: LightRagServerProbe }) {
  const { token } = theme.useToken();
  if (!probe.ok) {
    return (
      <Alert
        type="error"
        showIcon
        icon={<WarningOutlined style={{ fontSize: 14 }} />}
        style={{
          fontSize: 12,
          border: `1px solid ${RED_ERROR_BORDER}`,
          background: RED_ERROR_BG,
          color: RED_ERROR_TEXT,
        }}
        message="无法连接"
        description={
          probe.error ? (
            <span style={{ lineHeight: 1.6 }}>{probe.error}</span>
          ) : undefined
        }
      />
    );
  }
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        borderRadius: 8,
        border: `1px solid ${token.colorBorder}`,
        background: token.colorFillQuaternary,
        padding: "10px 12px",
        fontSize: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontWeight: 500,
          color: EMERALD_TEXT,
        }}
      >
        <CheckOutlined />
        已连接到 LightRAG server
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 12,
          rowGap: 4,
          fontSize: 11.5,
          color: token.colorTextSecondary,
        }}
      >
        {probe.core_version && <span>{`内核 ${probe.core_version}`}</span>}
        <span>{probe.auth_required ? "API 密钥已通过" : "开放访问"}</span>
      </div>
    </div>
  );
}

function LinkModeFields({
  providers,
  linkSource,
  setLinkSource,
  linkIsObsidian,
  folderPath,
  setFolderPath,
  submitting,
  probing,
  probe,
  onProbe,
}: {
  providers: RagProviderSummary[];
  linkSource: string;
  setLinkSource: (id: string) => void;
  linkIsObsidian: boolean;
  folderPath: string;
  setFolderPath: (value: string) => void;
  submitting: boolean;
  probing: boolean;
  probe: LinkedFolderProbe | null;
  onProbe: () => void;
}) {
  const { token } = theme.useToken();
  return (
    <>
      <div>
        <label style={labelStyle(token)}>来源</label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 8,
          }}
        >
          {providers.map((p) => {
            const selected = !linkIsObsidian && linkSource === p.id;
            const disabled = submitting || !p.linkable;
            return (
              <SelectCard
                key={p.id}
                selected={selected}
                disabled={disabled}
                onClick={() => setLinkSource(p.id)}
                title={
                  !p.linkable
                    ? "该引擎的索引在云端，无法关联。"
                    : undefined
                }
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: token.colorText,
                    }}
                  >
                    {p.name}
                  </span>
                  {!p.linkable ? (
                    <MutedBadge token={token} text="云端索引" />
                  ) : selected ? (
                    <CheckOutlined
                      style={{ fontSize: 14, color: token.colorPrimary }}
                    />
                  ) : null}
                </div>
                <span
                  style={{
                    fontSize: 11.5,
                    lineHeight: 1.4,
                    color: token.colorTextSecondary,
                  }}
                >
                  {p.description}
                </span>
              </SelectCard>
            );
          })}

          {/* Obsidian — a live vault, no index. */}
          <SelectCard
            selected={linkIsObsidian}
            disabled={submitting}
            onClick={() => setLinkSource(OBSIDIAN_SOURCE)}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 13,
                  fontWeight: 500,
                  color: token.colorText,
                }}
              >
                <FolderOpenOutlined style={{ fontSize: 14 }} />
                Obsidian
              </span>
              {linkIsObsidian && (
                <CheckOutlined
                  style={{ fontSize: 14, color: token.colorPrimary }}
                />
              )}
            </div>
            <span
              style={{
                fontSize: 11.5,
                lineHeight: 1.4,
                color: token.colorTextSecondary,
              }}
            >
              {"实时的 Obsidian 库——就地浏览与编辑，不建索引。"}
            </span>
          </SelectCard>
        </div>
      </div>

      <div>
        <label style={labelStyle(token)}>
          {linkIsObsidian ? "Vault 路径" : "文件夹路径"}
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <Input
            value={folderPath}
            onChange={(event) => setFolderPath(event.target.value)}
            disabled={submitting}
            placeholder={
              linkIsObsidian ? EXAMPLE_VAULT_PATH : EXAMPLE_INDEX_PATH
            }
            style={{ fontFamily: MONO_FONT, fontSize: 12.5 }}
          />
          {!linkIsObsidian && (
            <Button
              onClick={onProbe}
              disabled={
                submitting || probing || folderPath.trim().length === 0
              }
              loading={probing}
              icon={<FolderOpenOutlined />}
              style={{ flexShrink: 0, fontSize: 12 }}
            >
              检查文件夹
            </Button>
          )}
        </div>
        <p
          style={{
            margin: "4px 0 0",
            fontSize: 11,
            color: token.colorTextSecondary,
          }}
        >
          {linkIsObsidian
            ? "本机上 vault 文件夹的绝对路径。"
            : "本机上某个知识库文件夹的绝对路径——不会复制任何内容。"}
        </p>
      </div>

      {!linkIsObsidian && probe && <ProbeVerdict probe={probe} />}
    </>
  );
}

function ProbeVerdict({ probe }: { probe: LinkedFolderProbe }) {
  const { token } = theme.useToken();
  if (!probe.ok) {
    return (
      <Alert
        type="error"
        showIcon
        icon={<WarningOutlined style={{ fontSize: 14 }} />}
        style={{
          fontSize: 12,
          border: `1px solid ${RED_ERROR_BORDER}`,
          background: RED_ERROR_BG,
          color: RED_ERROR_TEXT,
        }}
        message="该文件夹无法关联"
        description={
          probe.error ? (
            <span style={{ lineHeight: 1.6 }}>{probe.error}</span>
          ) : undefined
        }
      />
    );
  }

  const compatible = probe.embedding.compatible;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        borderRadius: 8,
        border: `1px solid ${token.colorBorder}`,
        background: token.colorFillQuaternary,
        padding: "10px 12px",
        fontSize: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontWeight: 500,
          color: EMERALD_TEXT,
        }}
      >
        <CheckOutlined />
        找到可用索引
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 12,
          rowGap: 4,
          fontSize: 11.5,
          color: token.colorTextSecondary,
        }}
      >
        {probe.version && (
          <span style={{ fontFamily: MONO_FONT }}>{probe.version}</span>
        )}
        {probe.doc_count != null && (
          <span>{`${probe.doc_count} 篇文档`}</span>
        )}
        {compatible === true && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              color: EMERALD_TEXT,
            }}
          >
            <CheckOutlined style={{ fontSize: 12 }} />
            embedding 模型匹配
          </span>
        )}
      </div>
      {probe.warnings.map((warning, index) => (
        <p
          key={index}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            margin: 0,
            lineHeight: 1.6,
            color: AMBER_BADGE_TEXT,
          }}
        >
          <WarningOutlined
            style={{ marginTop: 3, fontSize: 14, flexShrink: 0 }}
          />
          <span>{warning}</span>
        </p>
      ))}
    </div>
  );
}
