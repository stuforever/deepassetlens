/**
 * ServiceConfigEditor —— 七类服务统一编辑器（1:1 复刻自 DeepTutor 原仓
 * web/components/settings/ServiceConfigEditor.tsx，1295 行，整件逐段移植）。
 *
 * 服务段：llm / embedding / search / tts / stt / imagegen / videogen
 * （SERVICE_LABEL 逐字保留；search 无模型卡、stt 无专属模型字段——语义同源；
 *   document-parsing / mineru 不在本件，分别为设置页与 MinerUEngineSettings.tsx）。
 *
 * 替换点：
 *  - "use client" 删除；react-i18next（useTranslation / t()）→ 本文件 ZH 译文表 +
 *    本地 t(key, vars)（zh/app.json 扁平键=英文原文逐条收录；未收录键按 i18next
 *    回退直出原 key——原仓 zh 亦未收录的 9 键保留英文："Output format"、"Image size"、
 *    "Quality / Style"、"Aspect ratio"、"Duration / Resolution"、"seconds"、
 *    "Provider-specific voice name…"、"Default pixel size…"、"Defaults sent…"）。
 *  - lucide-react → @ant-design/icons 语义就近映射表：
 *      CheckCircle2→CheckCircleOutlined   ChevronDown→DownOutlined
 *      Eye→EyeOutlined                    EyeOff→EyeInvisibleOutlined
 *      Info→InfoCircleOutlined            Loader2→LoadingOutlined(spin)
 *      Pencil→EditOutlined                Plus→PlusOutlined
 *      Terminal→CodeOutlined              Trash2→DeleteOutlined
 *  - Tailwind → antd(props)+内联 style 对象（禁 tailwind）。颜色映射：
 *      var(--border)→#E2E8F0  var(--foreground)→#0F172A  var(--muted-foreground)→#64748B
 *      var(--muted)→#f4f4f5   var(--card)/var(--background)→#fff
 *      var(--primary)/var(--ring)→theme tokens primary；red-500/emerald-500/amber-600
 *      按原 Tailwind 色值字面量。hover/focus 内联无法表达的用 hoverProps/focusProps
 *      小助手等价（BookCreator hoverBg 先例）；dark: 变体 tupu 无暗色通道，取亮色值。
 *  - <select>/<option> 保留原生控件：shared.tsx 的 selectClass/selectOptionClass
 *    即原生 select 语义（appearance-none + 手绘 ChevronDown 覆盖层），且与并行件
 *    DimensionField 的 nativeSelectClass 同构；覆盖层映射为 DownOutlined 覆盖层。
 *    inputClass/selectClass/selectOptionClass 按并行 shared 落盘契约（等价 CSS 类名
 *    字符串，模块加载时注入 <style id="dsh-settings-shared-styles">）以 className
 *    消费——与源仓 className={...} 逐字同构；provider select 的 pl-9 以 style
 *    paddingLeft 等价叠加，API Key 的 pr-10/font-mono 与 textarea 的 min-h/resize 同理。
 *    focusProps 仅保留于两处自定义重命名输入（token 类自带 :focus 规则）。
 *  - 群组 hover 提示（group/info + role="tooltip" CSS 气泡）→ antd Tooltip（文案不变）。
 *  - next/* 无引用；组件对外签名 { service: ServiceName } 与源码逐字一致（无 onChanged）。
 *  - ProviderIcon（源 @/components/common/ProviderIcon）→ 本仓已有同源 1:1 移植件
 *    pages/tutor/h5/h5shared/ProviderIcon（provider/size props 兼容）；源处的定位
 *    className 以包裹 span 的 style 等价（禁 tailwind）。
 *  - 兄弟件 './SettingsContext' './shared' './DimensionField' './codex-profile'
 *    './profile-naming' './search-providers' './CodexOAuthCard' 按源名相对导入
 *    （并行批同步落盘，按名 import 不自造）。
 *  - data-testid / data-tour / data-active / role / aria-* 全部逐字保留（对拍依赖）。
 */
import { useState } from "react";
import type {
  CSSProperties,
  FocusEvent as ReactFocusEvent,
  MouseEvent as ReactMouseEvent,
} from "react";
import {
  CheckCircleOutlined,
  CodeOutlined,
  CopyOutlined,
  DeleteOutlined,
  DownOutlined,
  EditOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { Tooltip, Select as AntSelect } from "antd"; // R5批②：原生 select → antd（R#2 续批——provider 级联/previousLabel diff 副作用逐字保留）

import ProviderIcon from "../../pages/tutor/h5/h5shared/ProviderIcon";
import { CodexOAuthCard } from "./CodexOAuthCard";
import { isCodexOAuthProfile, isManagedCodexProfile } from "./codex-profile";
import {
  type CatalogModel,
  type CatalogProfile,
  type LlmContextWindowDetection,
  type ServiceName,
  getActiveModel,
  getActiveProfile,
  useSettings,
} from "./SettingsContext";
import { DimensionField } from "./DimensionField";
import { nextProfileName } from "./profile-naming";
import { searchProviderFields } from "./search-providers";
import {
  activeProfileDetail,
  deprecatedSearchProviders,
  formatContextWindowSource,
  inputClass,
  selectClass,
  selectOptionClass,
  stringifyExtraHeaders,
  supportedSearchProviders,
} from "./shared";
import { colors } from "../../theme/tokens";

// ── zh/app.json 原译文替换表（t() 中文直出；未收录键按 i18next 回退直出原 key）──
const ZH: Record<string, string> = {
  "LLM": "LLM",
  "Embedding": "嵌入模型",
  "Search": "搜索",
  "Text-to-Speech": "语音合成",
  "Speech-to-Text": "语音识别",
  "Image Generation": "文生图",
  "Video Generation": "文生视频",
  "Backend unreachable — model endpoints will appear once the connection is restored. See the banner above for details.":
    "无法连接后端——连接恢复后模型端点会自动显示。详见上方提示横幅。",
  "Model endpoints are assigned by your administrator. You can still personalize theme and language here.":
    "模型端点由管理员分配。你仍可在此处自定义主题和语言。",
  "Profiles": "配置",
  "Double-click to rename": "双击重命名",
  "Rename profile": "重命名配置文件",
  "Permanently remove the currently selected profile.": "永久删除当前选中的配置文件。",
  "Delete “{{name}}”": "删除 “{{name}}”",
  "Delete profile": "删除当前配置文件",
  "Provider connection": "提供商连接",
  "Profile": "+ 新建配置",
  "Models": "模型列表",
  "Model": "模型",
  "Delete": "删除",
  "Duplicate profile": "复制配置",
  "Duplicate the currently selected profile with its models.": "复制当前配置及其模型列表。",
  "Rename model": "重命名模型",
  "Model ID": "模型 ID",
  "Context Window": "上下文窗口",
  "Dimension": "维度",
  "Send dimensions": "发送 dimensions 参数",
  "Some embedding models (e.g. Qwen text-embedding-v4) reject the `dimensions` request param. Turn this off if your provider returns HTTP 400.":
    "部分 embedding 模型（如 Qwen text-embedding-v4）不支持 `dimensions` 请求参数。若你的服务返回 HTTP 400，请关闭此开关。",
  "Voice": "语音",
  "Diagnostics": "诊断",
  "Run test": "运行测试",
  "Collapse diagnostics": "收起诊断",
  "Expand diagnostics": "展开诊断",
  "Streams config snapshot, request target, response summary, and service-specific validation for the active {{service}} profile.":
    "为当前 {{service}} 配置文件流式输出配置快照、请求目标、响应摘要和服务特定验证。",
  "Waiting for test run...": "等待测试运行...",
  "No profiles configured. Add a profile to start.": "暂无配置文件。添加一个以开始使用。",
  "Source": "来源",
  "Detected value matches your current setting": "检测值与当前设置一致",
  "Detected": "检测到",
  "Apply": "应用",
  "Provider": "提供商",
  "Select provider...": "选择提供商...",
  "Perplexity requires API key. It will fail hard without credentials.":
    "Perplexity 需要 API 密钥，缺少凭证将无法使用。",
  "Supported provider.": "受支持的提供商。",
  "Deprecated provider. Switch to brave/tavily/jina/searxng/duckduckgo/perplexity.":
    "已弃用的提供商。请切换到 brave/tavily/jina/searxng/duckduckgo/perplexity。",
  "Unsupported provider. Use brave/tavily/jina/searxng/duckduckgo/perplexity.":
    "不受支持的提供商。请使用 brave/tavily/jina/searxng/duckduckgo/perplexity。",
  "Endpoint URL": "端点 URL",
  "Base URL": "Base URL",
  "Embedding requests are sent to this URL exactly; DeepTutor does not append /embeddings or /api/embed at request time.":
    "向量化请求会直接发送到此 URL；DeepTutor 不会在请求时追加 /embeddings 或 /api/embed。",
  "Required — without it, search falls back to DuckDuckGo.": "必填——缺少它，搜索将回退到 DuckDuckGo。",
  "API Key": "API Key",
  "Hide API key": "隐藏 API Key",
  "Show API key": "显示 API Key",
  "Extra (optional)": "Extra（可选）",
  "API version and proxy": "API 版本和代理",
  "API version and extra request headers": "API 版本和额外请求头",
  "API Version": "API 版本",
  "Optional": "可选",
  "Proxy": "代理",
  "http://127.0.0.1:7890 (optional)": "http://127.0.0.1:7890（可选）",
  "Extra Headers (JSON)": "额外请求头 (JSON)",
};

/** 本地 t()：ZH 收录键出中文，未收录键回退原 key（i18next 回退语义一致）。 */
const t = (key: string, vars?: Record<string, unknown>): string => {
  const base = ZH[key] ?? key;
  if (!vars) return base;
  return Object.entries(vars).reduce(
    (acc, [k, v]) => acc.split(`{{${k}}}`).join(String(v)),
    base,
  );
};

// ── Tailwind 变量到字面量的最小映射（BookCreator 先例）────────────────────
const BORDER = colors.border; // var(--border)
const FG = colors.textPrimary; // var(--foreground)
const MUTED = colors.textSecondary; // var(--muted-foreground)
const MUTED_BG = "#f4f4f5"; // var(--muted)
const RED_500 = "#ef4444"; // tailwind red-500
const EMERALD_500 = "#10b981"; // tailwind emerald-500
const EMERALD_600 = "#059669"; // tailwind emerald-600
const AMBER_600 = "#d97706"; // tailwind amber-600（dark:amber-400 不取，无暗色通道）
const MONO =
  "ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace";
const TRUNCATE: CSSProperties = {
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
};
const fgA = (a: number) => `rgba(15, 23, 42, ${a})`; // foreground 透明度变体
const mutedA = (a: number) => `rgba(100, 116, 139, ${a})`; // muted-foreground 透明度变体
const borderA = (a: number) => `rgba(226, 232, 240, ${a})`; // border 透明度变体

/** hover 行内样式等价（Tailwind hover:* 无法用纯内联样式表达，BookCreator 先例）。 */
function hoverProps(patch: CSSProperties): {
  onMouseEnter: (e: ReactMouseEvent<HTMLElement>) => void;
  onMouseLeave: (e: ReactMouseEvent<HTMLElement>) => void;
} {
  return {
    onMouseEnter: (e) => {
      Object.assign(e.currentTarget.style, patch);
    },
    onMouseLeave: (e) => {
      for (const key of Object.keys(patch)) {
        e.currentTarget.style.removeProperty(
          key.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`),
        );
      }
    },
  };
}

/** focus 高亮等价（fieldControlClass 的 focus:border-ring 内联等价）。 */
const FOCUS_PROPS = {
  onFocus: (e: ReactFocusEvent<HTMLElement>) => {
    e.currentTarget.style.borderColor = colors.primary;
  },
  onBlur: (e: ReactFocusEvent<HTMLElement>) => {
    e.currentTarget.style.borderColor = BORDER;
  },
};

const SERVICE_LABEL: Record<ServiceName, string> = {
  llm: "LLM",
  embedding: "Embedding",
  search: "Search",
  tts: "Text-to-Speech",
  stt: "Speech-to-Text",
  imagegen: "Image Generation",
  videogen: "Video Generation",
};

export function ServiceConfigEditor({ service }: { service: ServiceName }) {
  const {
    draft,
    catalogEditable,
    settingsError,
    providers,
    language,
    embeddingCapabilities,
    embeddingDefaultDim,
    logs,
    testRunning,
    mutateCatalog,
    addProfile,
    duplicateProfile,
    removeActiveProfile,
    addModel,
    removeActiveModel,
    updateProfileField,
    updateModelField,
    updateModelBoolField,
    updateContextWindowField,
    llmContextDetection,
    applyDetectedContextWindow,
    runDetailedTest,
  } = useSettings();

  const activeProfile = getActiveProfile(draft, service);
  const activeModel = getActiveModel(draft, service);
  const activeProviderValue =
    service === "search"
      ? activeProfile?.provider || ""
      : activeProfile?.binding || "";
  const activeProviderOption = (providers[service] || []).find(
    (option) => option.value === activeProviderValue,
  );
  const isManagedCodex = isManagedCodexProfile(activeProfile);
  const isCodexOAuth = isCodexOAuthProfile(
    service,
    activeProviderValue,
    activeProviderOption,
    activeProfile,
  );

  const [showApiKey, setShowApiKey] = useState(false);
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
  const [editingModelId, setEditingModelId] = useState<string | null>(null);
  const [editingModelName, setEditingModelName] = useState("");
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [editingProfileName, setEditingProfileName] = useState("");

  // Reset API-key visibility whenever we land on a different profile or
  // switch services — same effect the old code had, but using React's
  // documented "store previous prop in state" pattern so it happens during
  // render rather than in a useEffect (which the linter forbids).
  const profileKey = `${service}:${activeProfile?.id ?? "none"}`;
  const [lastProfileKey, setLastProfileKey] = useState(profileKey);
  if (lastProfileKey !== profileKey) {
    setLastProfileKey(profileKey);
    if (showApiKey) setShowApiKey(false);
  }

  const searchProviderRaw =
    service === "search"
      ? (activeProfile?.provider || "").trim().toLowerCase()
      : "";
  const showSearchProviderWarning =
    service === "search" && Boolean(searchProviderRaw);
  const isDeprecatedSearchProvider =
    deprecatedSearchProviders.has(searchProviderRaw);
  const isSupportedSearchProvider = supportedSearchProviders.includes(
    searchProviderRaw as (typeof supportedSearchProviders)[number],
  );
  const isPerplexityMissingKey =
    service === "search" &&
    searchProviderRaw === "perplexity" &&
    !String(activeProfile?.api_key || "").trim();
  const activeLlmDetection =
    service === "llm" &&
    llmContextDetection?.profileId === draft.services.llm.active_profile_id &&
    llmContextDetection?.modelId === draft.services.llm.active_model_id
      ? llmContextDetection
      : null;

  const startModelRename = (model: CatalogModel) => {
    setEditingModelId(model.id);
    setEditingModelName(model.name || model.model || "");
  };

  const commitModelRename = (modelId: string) => {
    const fallbackIndex =
      activeProfile?.models.findIndex((model) => model.id === modelId) ?? -1;
    const fallbackName = defaultModelLabel(language, fallbackIndex + 1);
    const nextName = editingModelName.trim() || fallbackName;
    mutateCatalog((next) => {
      const profile = getActiveProfile(next, service);
      const model = profile?.models.find((item) => item.id === modelId);
      if (model) model.name = nextName;
    });
    setEditingModelId(null);
    setEditingModelName("");
  };

  const cancelModelRename = () => {
    setEditingModelId(null);
    setEditingModelName("");
  };

  const startProfileRename = (profile: CatalogProfile) => {
    setEditingProfileId(profile.id);
    setEditingProfileName(profile.name || "");
  };

  const commitProfileRename = (profileId: string) => {
    const nextName = editingProfileName.trim();
    if (nextName) {
      mutateCatalog((next) => {
        const profile = next.services[service].profiles.find(
          (item) => item.id === profileId,
        );
        if (profile) profile.name = nextName;
      });
    }
    setEditingProfileId(null);
    setEditingProfileName("");
  };

  const cancelProfileRename = () => {
    setEditingProfileId(null);
    setEditingProfileName("");
  };

  if (!catalogEditable) {
    // catalogEditable=false covers two unrelated cases: settings fetch failed,
    // or multi-user grant denied. Split them so a Docker user without the
    // 8001 port mapped does not see an "assigned by administrator" hint.
    if (settingsError) {
      return (
        <div
          style={{
            borderRadius: 12,
            border: `1px dashed ${BORDER}`,
            padding: "40px 20px",
            textAlign: "center",
            fontSize: 13,
            color: MUTED,
          }}
        >
          {t(
            "Backend unreachable — model endpoints will appear once the connection is restored. See the banner above for details.",
          )}
        </div>
      );
    }
    return (
      <div
        style={{
          borderRadius: 12,
          border: `1px dashed ${BORDER}`,
          padding: "40px 20px",
          textAlign: "center",
          fontSize: 13,
          color: MUTED,
        }}
      >
        {t(
          "Model endpoints are assigned by your administrator. You can still personalize theme and language here.",
        )}
      </div>
    );
  }

  // 小型描边按钮（新增 Profile / 新增 Model / 运行测试共用样式，与源 className 一致）。
  const smallOutlineBtn: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    borderRadius: 8,
    border: `1px solid ${borderA(0.5)}`,
    padding: "4px 10px",
    fontSize: 12,
    fontFamily: "inherit",
    color: MUTED,
    background: "transparent",
    cursor: "pointer",
    transition: "border-color 0.15s, color 0.15s",
  };
  const smallOutlineHover = hoverProps({ borderColor: BORDER, color: FG });

  return (
    <div
      data-tour={`tour-${service}`}
      data-testid={`service-editor-${service}`}
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {activeProfile ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "200px minmax(0, 1fr)",
            alignItems: "start",
            gap: 20,
          }}
        >
          {/* ── Profile list (sticky so it stays put while the editor scrolls) ── */}
          <aside
            data-testid={`service-profile-list-${service}`}
            style={{
              position: "sticky",
              top: 16,
              alignSelf: "start",
              borderRadius: 12,
              border: `1px solid ${borderA(0.6)}`,
              background: "rgba(255, 255, 255, 0.4)",
              padding: 8,
            }}
          >
            <div
              style={{
                padding: "4px 8px 8px",
                fontSize: 11,
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.025em",
                color: mutedA(0.7),
              }}
            >
              {t("Profiles")}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {draft.services[service].profiles.map((profile, profileIndex) => {
                const isActive =
                  profile.id === draft.services[service].active_profile_id;
                const profileDetail = activeProfileDetail(profile, service, t);
                const isManagedProfile = isManagedCodexProfile(profile);
                const isEditing =
                  editingProfileId === profile.id && !isManagedProfile;
                return (
                  <div
                    key={profile.id}
                    role="button"
                    tabIndex={isEditing ? -1 : 0}
                    data-testid={`service-profile-${service}-${profileIndex}`}
                    data-active={isActive || undefined}
                    onClick={() => {
                      if (isEditing) return;
                      mutateCatalog((next) => {
                        next.services[service].active_profile_id = profile.id;
                        if (service !== "search") {
                          next.services[service].active_model_id =
                            profile.models[0]?.id ?? null;
                        }
                      });
                    }}
                    onDoubleClick={() => {
                      if (!isManagedProfile) startProfileRename(profile);
                    }}
                    onKeyDown={(e) => {
                      if (isEditing) return;
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        mutateCatalog((next) => {
                          next.services[service].active_profile_id = profile.id;
                          if (service !== "search") {
                            next.services[service].active_model_id =
                              profile.models[0]?.id ?? null;
                          }
                        });
                      }
                    }}
                    title={
                      isEditing || isManagedProfile
                        ? undefined
                        : t("Double-click to rename")
                    }
                    style={{
                      position: "relative",
                      cursor: "pointer",
                      borderRadius: 8,
                      padding: "8px 12px",
                      textAlign: "left",
                      transition: "background-color 0.15s, color 0.15s",
                      background: isActive
                        ? "rgba(244, 244, 245, 0.7)"
                        : "transparent",
                      color: isActive ? FG : MUTED,
                      ...(isActive
                        ? {}
                        : hoverProps({
                            backgroundColor: "rgba(244, 244, 245, 0.3)",
                          })),
                    }}
                  >
                    {isActive && (
                      <span
                        style={{
                          position: "absolute",
                          top: 8,
                          bottom: 8,
                          left: 0,
                          width: 2,
                          borderRadius: "0 999px 999px 0",
                          background: fgA(0.8),
                        }}
                      />
                    )}
                    {isEditing ? (
                      <input
                        autoFocus
                        data-testid={`service-profile-rename-${service}`}
                        style={{
                          display: "block",
                          width: "100%",
                          borderRadius: 4,
                          border: `1px solid ${BORDER}`,
                          background: "#fff",
                          padding: "2px 6px",
                          fontSize: 13,
                          fontFamily: "inherit",
                          fontWeight: 500,
                          color: FG,
                          outline: "none",
                          boxSizing: "border-box",
                        }}
                        {...FOCUS_PROPS}
                        value={editingProfileName}
                        onChange={(e) => setEditingProfileName(e.target.value)}
                        onBlur={() => commitProfileRename(profile.id)}
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.currentTarget.blur();
                          }
                          if (e.key === "Escape") {
                            e.preventDefault();
                            cancelProfileRename();
                          }
                        }}
                        aria-label={t("Rename profile")}
                      />
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        <ProviderIcon
                          provider={
                            service === "search"
                              ? profile.provider
                              : profile.binding
                          }
                          size={13}
                        />
                        <div
                          style={{
                            minWidth: 0,
                            flex: 1,
                            fontSize: 13,
                            lineHeight: 1.25,
                            fontWeight: isActive ? 600 : 500,
                            ...TRUNCATE,
                          }}
                        >
                          {profile.name}
                        </div>
                        {!isManagedProfile && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              startProfileRename(profile);
                            }}
                            data-testid={`service-profile-edit-${service}-${profileIndex}`}
                            style={{
                              marginRight: -4,
                              flexShrink: 0,
                              borderRadius: 6,
                              padding: 4,
                              border: "none",
                              background: "transparent",
                              cursor: "pointer",
                              color: mutedA(0.6),
                              transition: "background-color 0.15s, color 0.15s",
                            }}
                            {...hoverProps({
                              backgroundColor: MUTED_BG,
                              color: FG,
                            })}
                            aria-label={t("Rename profile")}
                            title={t("Rename profile")}
                          >
                            <EditOutlined style={{ fontSize: 12 }} />
                          </button>
                        )}
                      </div>
                    )}
                    <div
                      style={{
                        marginTop: 2,
                        fontSize: 11,
                        lineHeight: 1.25,
                        color: mutedA(0.7),
                        ...TRUNCATE,
                      }}
                    >
                      {profileDetail}
                    </div>
                  </div>
                );
              })}
            </div>
            <div
              style={{
                marginTop: 8,
                borderTop: `1px solid ${borderA(0.4)}`,
                paddingTop: 8,
              }}
            >
              {/* UX3修BUG：复制当前档（含模型/能力位/Key）——草稿级副本，保存草稿后经③适配器落库。
                  此前后端 /duplicate 端点无 UI 入口（孤儿能力），用户侧「复制」不可用。 */}
              <button
                onClick={() => duplicateProfile(service)}
                disabled={!activeProfile || isManagedCodex}
                data-testid={`service-duplicate-profile-${service}`}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 8,
                  padding: "6px 12px",
                  textAlign: "left",
                  fontSize: 11,
                  fontFamily: "inherit",
                  color: mutedA(0.6),
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  opacity: !activeProfile || isManagedCodex ? 0.3 : 1,
                  transition: "background-color 0.15s, color 0.15s",
                  marginBottom: 4,
                }}
                {...hoverProps({
                  backgroundColor: MUTED_BG,
                  color: FG,
                })}
                title={
                  activeProfile && !isManagedCodex
                    ? t("Duplicate the currently selected profile with its models.")
                    : undefined
                }
              >
                <CopyOutlined style={{ fontSize: 12, flexShrink: 0 }} />
                {t("Duplicate profile")}
              </button>
              <button
                onClick={() => removeActiveProfile(service)}
                disabled={!activeProfile || isManagedCodex}
                data-testid={`service-delete-profile-${service}`}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 8,
                  padding: "6px 12px",
                  textAlign: "left",
                  fontSize: 11,
                  fontFamily: "inherit",
                  color: mutedA(0.6),
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  opacity: !activeProfile || isManagedCodex ? 0.3 : 1,
                  transition: "background-color 0.15s, color 0.15s",
                }}
                {...hoverProps({
                  backgroundColor: "rgba(239, 68, 68, 0.05)",
                  color: RED_500,
                })}
                title={
                  activeProfile && !isManagedCodex
                    ? t("Permanently remove the currently selected profile.")
                    : undefined
                }
              >
                <DeleteOutlined
                  style={{ fontSize: 12, flexShrink: 0 }}
                />
                <span style={TRUNCATE}>
                  {activeProfile
                    ? t("Delete “{{name}}”", { name: activeProfile.name })
                    : t("Delete profile")}
                </span>
              </button>
            </div>
          </aside>

          {/* ── Editor ── */}
          <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>
            <div
              style={{
                borderRadius: 12,
                border: `1px solid ${BORDER}`,
                padding: 20,
              }}
            >
              <div
                style={{
                  marginBottom: 16,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 500, color: FG }}>
                  {t("Provider connection")}
                </div>
                <button
                  type="button"
                  onClick={() => addProfile(service)}
                  data-testid={`service-add-profile-${service}`}
                  style={smallOutlineBtn}
                  {...smallOutlineHover}
                >
                  <PlusOutlined style={{ fontSize: 12 }} />
                  {t("Profile")}
                </button>
              </div>
              <ProfileFields
                service={service}
                profile={activeProfile}
                showApiKey={showApiKey}
                setShowApiKey={setShowApiKey}
                showSearchProviderWarning={showSearchProviderWarning}
                isSupportedSearchProvider={isSupportedSearchProvider}
                isDeprecatedSearchProvider={isDeprecatedSearchProvider}
                isPerplexityMissingKey={isPerplexityMissingKey}
              />
            </div>

            {service !== "search" && (
              <div
                style={{
                  borderRadius: 12,
                  border: `1px solid ${BORDER}`,
                  padding: 20,
                }}
              >
                <div
                  style={{
                    marginBottom: 16,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 500, color: FG }}>
                    {t("Models")}
                  </div>
                  {!isCodexOAuth && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => addModel(service)}
                        data-testid={`service-add-model-${service}`}
                        style={smallOutlineBtn}
                        {...smallOutlineHover}
                      >
                        <PlusOutlined style={{ fontSize: 12 }} />
                        {t("Model")}
                      </button>
                      <button
                        onClick={() => removeActiveModel(service)}
                        disabled={!activeModel}
                        data-testid={`service-delete-model-${service}`}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          fontSize: 11,
                          fontFamily: "inherit",
                          color: mutedA(0.4),
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          opacity: !activeModel ? 0.3 : 1,
                          transition: "color 0.15s",
                        }}
                        {...hoverProps({ color: RED_500 })}
                      >
                        <DeleteOutlined style={{ fontSize: 12 }} />
                        {t("Delete")}
                      </button>
                    </div>
                  )}
                </div>
                {activeProfile.models.length > 0 && (
                  <div
                    style={{
                      marginBottom: 16,
                      display: "flex",
                      flexWrap: "wrap",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    {activeProfile.models.map((model, index) => {
                      const isActive =
                        model.id === draft.services[service].active_model_id;
                      const label =
                        (model.name || "").trim() ||
                        defaultModelLabel(language, index + 1);
                      const metric =
                        service === "llm"
                          ? formatCompactTokens(model.context_window)
                          : service === "embedding"
                            ? formatDimensionBadge(model.dimension)
                            : service === "tts"
                              ? formatVoiceBadge(model.voice)
                              : "";
                      return (
                        <div key={model.id} style={{ minWidth: 0 }}>
                          {editingModelId === model.id && !isCodexOAuth ? (
                            <input
                              autoFocus
                              data-testid={`service-model-rename-${service}`}
                              style={{
                                height: 32,
                                width: 240,
                                borderRadius: 8,
                                border: `1px solid ${BORDER}`,
                                background: "#fff",
                                padding: "0 10px",
                                fontSize: 12.5,
                                fontFamily: "inherit",
                                color: FG,
                                outline: "none",
                                boxSizing: "border-box",
                              }}
                              {...FOCUS_PROPS}
                              value={editingModelName}
                              onChange={(e) =>
                                setEditingModelName(e.target.value)
                              }
                              onBlur={() => commitModelRename(model.id)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.currentTarget.blur();
                                }
                                if (e.key === "Escape") {
                                  e.preventDefault();
                                  cancelModelRename();
                                }
                              }}
                              aria-label={t("Rename model")}
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                mutateCatalog((next) => {
                                  next.services[service].active_model_id =
                                    model.id;
                                })
                              }
                              onDoubleClick={() => {
                                if (!isCodexOAuth) startModelRename(model);
                              }}
                              data-testid={`service-model-chip-${service}-${index}`}
                              data-active={isActive || undefined}
                              title={
                                isCodexOAuth
                                  ? undefined
                                  : t("Double-click to rename")
                              }
                              style={{
                                display: "inline-flex",
                                height: 32,
                                alignItems: "center",
                                gap: 6,
                                borderRadius: 8,
                                padding: "0 10px",
                                fontSize: 12.5,
                                fontFamily: "inherit",
                                border: "none",
                                cursor: "pointer",
                                transition: "background-color 0.15s, color 0.15s",
                                background: isActive ? MUTED_BG : "transparent",
                                color: isActive ? FG : MUTED,
                                ...(isActive
                                  ? {}
                                  : hoverProps({
                                      backgroundColor:
                                        "rgba(244, 244, 245, 0.4)",
                                    })),
                              }}
                            >
                              {isActive && (
                                <CheckCircleOutlined
                                  style={{
                                    fontSize: 12,
                                    flexShrink: 0,
                                    color: fgA(0.7),
                                  }}
                                />
                              )}
                              <span
                                style={{
                                  maxWidth: 280,
                                  lineHeight: 1,
                                  fontWeight: isActive ? 500 : 400,
                                  ...TRUNCATE,
                                }}
                              >
                                {label}
                              </span>
                              {metric && (
                                <span
                                  style={{
                                    flexShrink: 0,
                                    fontSize: 10.5,
                                    fontVariantNumeric: "tabular-nums",
                                    lineHeight: 1,
                                    color: mutedA(0.8),
                                  }}
                                >
                                  {metric}
                                </span>
                              )}
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                {activeModel && !isCodexOAuth && (
                  <div
                    style={{
                      display: "grid",
                      gap: 16,
                      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          marginBottom: 6,
                          fontSize: 12,
                          color: MUTED,
                        }}
                      >
                        {t("Model ID")}
                      </div>
                      <input
                        className={inputClass}
                        {...FOCUS_PROPS}
                        value={activeModel.model}
                        onChange={(e) =>
                          updateModelField(service, "model", e.target.value)
                        }
                        placeholder="gpt-4o"
                        data-testid={`service-model-id-${service}`}
                      />
                    </div>
                    {service === "llm" && (
                      <>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Context Window")}
                          </div>
                          <input
                            className={inputClass}
                            {...FOCUS_PROPS}
                            inputMode="numeric"
                            value={activeModel.context_window || ""}
                            onChange={(e) =>
                              updateContextWindowField(e.target.value)
                            }
                            placeholder="65536"
                            data-testid={`service-context-window-${service}`}
                          />
                          <ContextWindowMeta model={activeModel} />
                        </div>
                        <ContextWindowDetectionBanner
                          model={activeModel}
                          detection={activeLlmDetection}
                          onApply={applyDetectedContextWindow}
                        />
                      </>
                    )}
                    {service === "embedding" && (
                      <div>
                        <div
                          style={{
                            marginBottom: 6,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 8,
                          }}
                        >
                          <span style={{ fontSize: 12, color: MUTED }}>
                            {t("Dimension")}
                          </span>
                          <label
                            style={{
                              display: "inline-flex",
                              cursor: "pointer",
                              alignItems: "center",
                              gap: 6,
                              fontSize: 11,
                              color: MUTED,
                              userSelect: "none",
                            }}
                          >
                            <input
                              type="checkbox"
                              style={{
                                width: 12,
                                height: 12,
                                cursor: "pointer",
                                accentColor: FG,
                              }}
                              checked={activeModel.send_dimensions !== false}
                              onChange={(e) =>
                                updateModelBoolField(
                                  service,
                                  "send_dimensions",
                                  e.target.checked,
                                )
                              }
                              data-testid={`service-send-dimensions-${service}`}
                            />
                            <span>{t("Send dimensions")}</span>
                            <Tooltip
                              title={
                                <span>
                                  {t(
                                    "Some embedding models (e.g. Qwen text-embedding-v4) reject the `dimensions` request param. Turn this off if your provider returns HTTP 400.",
                                  )}
                                </span>
                              }
                            >
                              <span
                                tabIndex={0}
                                style={{
                                  display: "inline-flex",
                                  cursor: "help",
                                  outline: "none",
                                  opacity: 0.5,
                                }}
                              >
                                <InfoCircleOutlined style={{ fontSize: 12 }} />
                              </span>
                            </Tooltip>
                          </label>
                        </div>
                        <DimensionField
                          activeModel={activeModel}
                          activeBinding={activeProfile?.binding}
                          capabilities={embeddingCapabilities}
                          embeddingDefaultDim={embeddingDefaultDim}
                          inputClass={inputClass}
                          onChangeDimension={(value) =>
                            updateModelField(service, "dimension", value)
                          }
                        />
                      </div>
                    )}
                    {service === "tts" && (
                      <>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Voice")}
                          </div>
                          <input
                            className={inputClass}
                            {...FOCUS_PROPS}
                            value={activeModel.voice || ""}
                            onChange={(e) =>
                              updateModelField(service, "voice", e.target.value)
                            }
                            placeholder="alloy"
                            data-testid={`service-voice-${service}`}
                          />
                          <p
                            style={{
                              marginTop: 6,
                              marginBottom: 0,
                              fontSize: 11,
                              color: MUTED,
                            }}
                          >
                            {t(
                              "Provider-specific voice name, e.g. alloy (OpenAI) or model:voice (SiliconFlow).",
                            )}
                          </p>
                        </div>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Output format")}
                          </div>
                          <AntSelect
                            value={activeModel.response_format || "mp3"}
                            onChange={(v) =>
                              updateModelField(service, "response_format", v)
                            }
                            data-testid={`service-response-format-${service}`}
                            style={{ width: "100%" }}
                            options={["mp3", "wav", "opus", "aac", "flac", "pcm"].map(
                              (fmt) => ({ value: fmt, label: fmt }),
                            )}
                          />
                        </div>
                      </>
                    )}
                    {service === "imagegen" && (
                      <>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Image size")}
                          </div>
                          <input
                            className={inputClass}
                            {...FOCUS_PROPS}
                            value={activeModel.size || ""}
                            onChange={(e) =>
                              updateModelField(service, "size", e.target.value)
                            }
                            placeholder="1024x1024"
                            data-testid={`service-image-size-${service}`}
                          />
                          <p
                            style={{
                              marginTop: 6,
                              marginBottom: 0,
                              fontSize: 11,
                              color: MUTED,
                            }}
                          >
                            {t(
                              "Default pixel size sent with each request. Leave empty for the provider default.",
                            )}
                          </p>
                        </div>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Quality / Style")}
                          </div>
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr 1fr",
                              gap: 8,
                            }}
                          >
                            <input
                              className={inputClass}
                              {...FOCUS_PROPS}
                              value={activeModel.quality || ""}
                              onChange={(e) =>
                                updateModelField(
                                  service,
                                  "quality",
                                  e.target.value,
                                )
                              }
                              placeholder={t("quality (e.g. hd)")}
                              data-testid={`service-image-quality-${service}`}
                            />
                            <input
                              className={inputClass}
                              {...FOCUS_PROPS}
                              value={activeModel.style || ""}
                              onChange={(e) =>
                                updateModelField(
                                  service,
                                  "style",
                                  e.target.value,
                                )
                              }
                              placeholder={t("style (e.g. vivid)")}
                              data-testid={`service-image-style-${service}`}
                            />
                          </div>
                        </div>
                      </>
                    )}
                    {service === "videogen" && (
                      <>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Aspect ratio")}
                          </div>
                          <input
                            className={inputClass}
                            {...FOCUS_PROPS}
                            value={activeModel.aspect_ratio || ""}
                            onChange={(e) =>
                              updateModelField(
                                service,
                                "aspect_ratio",
                                e.target.value,
                              )
                            }
                            placeholder="16:9"
                            data-testid={`service-aspect-ratio-${service}`}
                          />
                          <p
                            style={{
                              marginTop: 6,
                              marginBottom: 0,
                              fontSize: 11,
                              color: MUTED,
                            }}
                          >
                            {t(
                              "Defaults sent with each request. Leave empty for the provider default.",
                            )}
                          </p>
                        </div>
                        <div>
                          <div
                            style={{
                              marginBottom: 6,
                              fontSize: 12,
                              color: MUTED,
                            }}
                          >
                            {t("Duration / Resolution")}
                          </div>
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr 1fr",
                              gap: 8,
                            }}
                          >
                            <input
                              className={inputClass}
                              {...FOCUS_PROPS}
                              inputMode="numeric"
                              value={activeModel.duration || ""}
                              onChange={(e) =>
                                updateModelField(
                                  service,
                                  "duration",
                                  e.target.value,
                                )
                              }
                              placeholder={t("seconds")}
                              data-testid={`service-video-duration-${service}`}
                            />
                            <input
                              className={inputClass}
                              {...FOCUS_PROPS}
                              value={activeModel.resolution || ""}
                              onChange={(e) =>
                                updateModelField(
                                  service,
                                  "resolution",
                                  e.target.value,
                                )
                              }
                              placeholder="720p"
                              data-testid={`service-video-resolution-${service}`}
                            />
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ── Diagnostics — per-service, inline ── */}
            <div
              style={{
                borderRadius: 12,
                border: `1px solid ${BORDER}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "14px 20px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setDiagnosticsOpen((v) => !v)}
                  style={{
                    display: "flex",
                    minWidth: 0,
                    flex: 1,
                    alignItems: "center",
                    gap: 8,
                    textAlign: "left",
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    padding: 0,
                    fontFamily: "inherit",
                  }}
                  aria-expanded={diagnosticsOpen}
                  data-testid={`service-diagnostics-toggle-${service}`}
                >
                  <CodeOutlined
                    style={{ fontSize: 14, color: MUTED, flexShrink: 0 }}
                  />
                  <span style={{ fontSize: 13, fontWeight: 500, color: FG }}>
                    {t("Diagnostics")}
                  </span>
                  {testRunning === service && (
                    <LoadingOutlined
                      spin
                      style={{ fontSize: 12, color: colors.primary }}
                    />
                  )}
                </button>
                <div
                  style={{
                    marginLeft: 12,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      if (!diagnosticsOpen) setDiagnosticsOpen(true);
                      runDetailedTest(service);
                    }}
                    disabled={testRunning !== null}
                    data-testid={`service-run-test-${service}`}
                    style={{
                      ...smallOutlineBtn,
                      opacity: testRunning !== null ? 0.4 : 1,
                      cursor: testRunning !== null ? "default" : "pointer",
                    }}
                    {...smallOutlineHover}
                  >
                    {t("Run test")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDiagnosticsOpen((v) => !v)}
                    style={{
                      fontSize: 12,
                      color: MUTED,
                      border: "none",
                      background: "transparent",
                      cursor: "pointer",
                      padding: 0,
                      transition: "color 0.15s",
                    }}
                    {...hoverProps({ color: FG })}
                    aria-label={
                      diagnosticsOpen
                        ? t("Collapse diagnostics")
                        : t("Expand diagnostics")
                    }
                    aria-expanded={diagnosticsOpen}
                    data-testid={`service-diagnostics-collapse-${service}`}
                  >
                    <DownOutlined
                      style={{
                        fontSize: 16,
                        transition: "transform 0.2s",
                        transform: diagnosticsOpen
                          ? "rotate(180deg)"
                          : "rotate(0deg)",
                      }}
                    />
                  </button>
                </div>
              </div>
              {diagnosticsOpen && (
                <div
                  style={{
                    borderTop: `1px solid ${BORDER}`,
                    padding: "16px 20px",
                  }}
                >
                  <p
                    style={{
                      marginBottom: 12,
                      fontSize: 12,
                      lineHeight: 1.625,
                      color: MUTED,
                    }}
                  >
                    {t(
                      "Streams config snapshot, request target, response summary, and service-specific validation for the active {{service}} profile.",
                      { service: t(SERVICE_LABEL[service]) },
                    )}
                  </p>
                  <pre
                    data-testid={`service-diagnostics-log-${service}`}
                    style={{
                      maxHeight: 360,
                      overflow: "auto",
                      borderRadius: 8,
                      background: "#0f0f0f",
                      padding: 16,
                      fontFamily: MONO,
                      fontSize: 12,
                      lineHeight: "24px",
                      color: "#777",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      margin: 0,
                    }}
                  >
                    {testRunning === service || logs
                      ? logs
                      : t("Waiting for test run...")}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            borderRadius: 12,
            border: `1px dashed ${BORDER}`,
            padding: "48px 20px",
            textAlign: "center",
            fontSize: 13,
            color: MUTED,
          }}
        >
          <div>{t("No profiles configured. Add a profile to start.")}</div>
          <button
            type="button"
            onClick={() => addProfile(service)}
            data-testid={`service-add-profile-${service}`}
            style={smallOutlineBtn}
            {...smallOutlineHover}
          >
            <PlusOutlined style={{ fontSize: 12 }} />
            {t("Profile")}
          </button>
        </div>
      )}
    </div>
  );
}

function defaultModelLabel(language: "en" | "zh", index: number): string {
  const safeIndex = index > 0 ? index : 1;
  return language === "zh" ? `模型${safeIndex}` : `Model ${safeIndex}`;
}

function formatCompactTokens(value: string | number | undefined): string {
  if (value === undefined || value === "") return "";
  const parsed =
    typeof value === "number"
      ? value
      : Number.parseInt(String(value).replace(/[^\d]/g, ""), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return "";
  if (parsed >= 1_000_000) {
    const m = parsed / 1_000_000;
    return `${m >= 10 ? m.toFixed(0) : m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (parsed >= 1_000) {
    const k = parsed / 1_000;
    return `${k >= 10 ? k.toFixed(0) : k.toFixed(1).replace(/\.0$/, "")}K`;
  }
  return String(parsed);
}

function formatVoiceBadge(value: string | undefined): string {
  const voice = (value || "").trim();
  if (!voice) return "";
  // "model:voice" → show just the voice segment to keep the chip compact.
  const tail = voice.includes(":")
    ? voice.slice(voice.lastIndexOf(":") + 1)
    : voice;
  return tail.length > 14 ? `${tail.slice(0, 13)}…` : tail;
}

function formatDimensionBadge(value: string | number | undefined): string {
  if (value === undefined || value === "") return "";
  const parsed =
    typeof value === "number"
      ? value
      : Number.parseInt(String(value).replace(/[^\d]/g, ""), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return "";
  return `${parsed}d`;
}

function formatIsoLocal(value: string | undefined): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ` +
    `${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`
  );
}

function ContextWindowMeta({ model }: { model: CatalogModel }) {
  if (!model.context_window) return null;
  const source = formatContextWindowSource(model.context_window_source, t);
  const updatedAt = formatIsoLocal(model.context_window_detected_at);
  return (
    <div
      style={{
        marginTop: 6,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        columnGap: 6,
        rowGap: 2,
        fontSize: 11,
        color: MUTED,
      }}
    >
      <span>{t("Source")}:</span>
      <span style={{ color: fgA(0.8) }}>{source}</span>
      {updatedAt && (
        <>
          <span style={{ color: mutedA(0.4) }}>·</span>
          <span title={model.context_window_detected_at}>{updatedAt}</span>
        </>
      )}
    </div>
  );
}

function ContextWindowDetectionBanner({
  model,
  detection,
  onApply,
}: {
  model: CatalogModel;
  detection: LlmContextWindowDetection | null;
  onApply: () => void;
}) {
  if (!detection) return null;
  const currentRaw = Number.parseInt(
    String(model.context_window || "").replace(/[^\d]/g, ""),
    10,
  );
  const matches =
    Number.isFinite(currentRaw) && currentRaw === detection.contextWindow;
  const detectedFormatted = detection.contextWindow.toLocaleString("en-US");
  const detectedAt = formatIsoLocal(detection.detectedAt);
  const source = formatContextWindowSource(detection.source, t);

  if (matches) {
    return (
      <div
        data-testid="service-detection-banner"
        data-state="match"
        style={{
          marginTop: 4,
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 8,
          rowGap: 4,
          borderRadius: 8,
          border: `1px solid ${"rgba(16, 185, 129, 0.3)"}`,
          background: "rgba(16, 185, 129, 0.05)",
          padding: "8px 12px",
          fontSize: 12,
          color: MUTED,
          gridColumn: "span 2",
        }}
      >
        <CheckCircleOutlined
          style={{ fontSize: 14, color: EMERALD_500, flexShrink: 0 }}
        />
        <span style={{ color: fgA(0.8) }}>
          {t("Detected value matches your current setting")}
        </span>
        <span style={{ color: mutedA(0.7) }}>
          ({detectedFormatted} · {source})
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="service-detection-banner"
      data-state="differs"
      style={{
        marginTop: 4,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        columnGap: 12,
        rowGap: 8,
        borderRadius: 8,
        border: `1px solid ${BORDER}`,
        background: "rgba(244, 244, 245, 0.3)",
        padding: "8px 12px",
        gridColumn: "span 2",
      }}
    >
      <div
        style={{
          display: "flex",
          minWidth: 0,
          flex: 1,
          flexWrap: "wrap",
          alignItems: "baseline",
          columnGap: 8,
          rowGap: 2,
          fontSize: 12,
        }}
      >
        <span style={{ color: MUTED }}>{t("Detected")}:</span>
        <span
          style={{
            fontFamily: MONO,
            fontSize: 13,
            fontWeight: 500,
            color: FG,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {detectedFormatted}
        </span>
        <span style={{ color: mutedA(0.8) }}>· {source}</span>
        {detectedAt && (
          <span style={{ color: mutedA(0.6) }}>· {detectedAt}</span>
        )}
      </div>
      <button
        type="button"
        onClick={onApply}
        data-testid="service-apply-detected"
        style={{
          flexShrink: 0,
          borderRadius: 6,
          border: `1px solid ${BORDER}`,
          background: "#fff",
          padding: "4px 10px",
          fontSize: 11.5,
          fontFamily: "inherit",
          fontWeight: 500,
          color: FG,
          cursor: "pointer",
          transition: "border-color 0.15s",
        }}
        {...hoverProps({ borderColor: FG })}
      >
        {t("Apply")}
      </button>
    </div>
  );
}

function ProfileFields({
  service,
  profile,
  showApiKey,
  setShowApiKey,
  showSearchProviderWarning,
  isSupportedSearchProvider,
  isDeprecatedSearchProvider,
  isPerplexityMissingKey,
}: {
  service: ServiceName;
  profile: CatalogProfile;
  showApiKey: boolean;
  setShowApiKey: (next: boolean | ((prev: boolean) => boolean)) => void;
  showSearchProviderWarning: boolean;
  isSupportedSearchProvider: boolean;
  isDeprecatedSearchProvider: boolean;
  isPerplexityMissingKey: boolean;
}) {
  const { providers, updateProfileField, updateProfileBoolField, updateModelField } = useSettings();
  const [extraOpen, setExtraOpen] = useState(false);

    // UX2批（LLM 配置改造）：思考模式/图片输入能力开关（仅 llm 服务渲染）
  const llmCapsUi =
    service === "llm" ? (
      <div style={{ marginTop: 12, display: "flex", gap: 18, alignItems: "center" }} data-testid="llm-capability-toggles">
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: FG }}>
          思考模式（深度推理）
          <input
            type="checkbox"
            checked={profile.default_mode === "deep"}
            onChange={(e) => updateProfileBoolField(service, "default_mode", e.target.checked)}
            data-testid="llm-thinking-toggle"
          />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: FG }}>
          图片输入
          <input
            type="checkbox"
            checked={profile.vision === true}
            onChange={(e) => updateProfileBoolField(service, "vision", e.target.checked)}
            data-testid="llm-vision-toggle"
          />
        </label>
      </div>
    ) : null;

const providerValue =
    service === "search" ? profile.provider || "" : profile.binding || "";
  const providerOption = (providers[service] || []).find(
    (option) => option.value === providerValue,
  );
  const isManagedCodex = isManagedCodexProfile(profile);
  const isCodexOAuth = isCodexOAuthProfile(
    service,
    providerValue,
    providerOption,
    profile,
  );

  const fields = isCodexOAuth
    ? { apiKey: false, baseUrl: false, baseUrlRequired: false }
    : service === "search"
      ? searchProviderFields(profile.provider)
      : { apiKey: true, baseUrl: true, baseUrlRequired: false };
  const searxngMissingBaseUrl =
    fields.baseUrlRequired && !String(profile.base_url || "").trim();

  return (
    <div
      style={{
        display: "grid",
        gap: 16,
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
      }}
    >
      <div style={{ gridColumn: "1 / -1" }}>
        <div
          style={{
            marginBottom: 6,
            fontSize: 12,
            color: MUTED,
          }}
        >
          {t("Provider")}
        </div>
        <AntSelect
          value={providerValue}
          disabled={isManagedCodex}
          data-testid={`service-provider-select-${service}`}
          prefix={
            providerValue ? (
              <ProviderIcon provider={providerValue} size={15} />
            ) : undefined
          }
          onChange={(val) => {
            const field = service === "search" ? "provider" : "binding";
            const options = providers[service] || [];
            const previousLabel =
              options.find((p) => p.value === providerValue)?.label ?? "";
            const match = options.find((p) => p.value === val);
            updateProfileField(service, field, val);
            // Keep an un-customized profile name tracking its provider.
            const renamed = nextProfileName(
              profile.name,
              previousLabel,
              match?.label ?? "",
            );
            if (renamed !== profile.name) {
              updateProfileField(service, "name", renamed);
            }
            if (match?.base_url) {
              updateProfileField(service, "base_url", match.base_url);
            }
            if (service === "embedding" && match?.default_dim) {
              updateModelField(service, "dimension", match.default_dim);
            }
            if (
              (service === "tts" ||
                service === "stt" ||
                service === "imagegen" ||
                service === "videogen") &&
              match?.default_model
            ) {
              updateModelField(service, "model", match.default_model);
            }
            if (service === "tts" && match?.default_voice) {
              updateModelField(service, "voice", match.default_voice);
            }
          }}
          style={{ width: "100%" }}
          options={[
            { value: "", label: t("Select provider...") },
            ...(providers[service] || []).map((p) => ({
              value: p.value,
              label: p.label,
            })),
          ]}
        />
        {showSearchProviderWarning && (
          <p
            style={{
              marginTop: 6,
              marginBottom: 0,
              fontSize: 11,
              color: isSupportedSearchProvider
                ? EMERALD_600
                : isDeprecatedSearchProvider
                  ? AMBER_600
                  : RED_500,
            }}
          >
            {isSupportedSearchProvider
              ? isPerplexityMissingKey
                ? t(
                    "Perplexity requires API key. It will fail hard without credentials.",
                  )
                : t("Supported provider.")
              : isDeprecatedSearchProvider
                ? t(
                    "Deprecated provider. Switch to brave/tavily/jina/searxng/duckduckgo/perplexity.",
                  )
                : t(
                    "Unsupported provider. Use brave/tavily/jina/searxng/duckduckgo/perplexity.",
                  )}
          </p>
        )}
      </div>
      {isCodexOAuth && (
        <div style={{ gridColumn: "1 / -1" }}>
          <CodexOAuthCard />
        </div>
      )}
      {fields.baseUrl && (
        <div style={{ gridColumn: "1 / -1" }}>
          <div
            style={{
              marginBottom: 6,
              fontSize: 12,
              color: MUTED,
            }}
          >
            {service === "embedding" ? t("Endpoint URL") : t("Base URL")}
          </div>
          <input
            className={inputClass}
            {...FOCUS_PROPS}
            value={profile.base_url}
            onChange={(e) =>
              updateProfileField(service, "base_url", e.target.value)
            }
            data-testid={`service-base-url-${service}`}
            placeholder={
              service === "embedding"
                ? "https://api.openai.com/v1/embeddings"
                : service === "search"
                  ? "http://localhost:8888"
                  : "https://api.openai.com/v1"
            }
          />
          {service === "embedding" && (
            <p
              style={{
                marginTop: 6,
                marginBottom: 0,
                fontSize: 11,
                color: MUTED,
              }}
            >
              {t(
                "Embedding requests are sent to this URL exactly; DeepTutor does not append /embeddings or /api/embed at request time.",
              )}
            </p>
          )}
          {searxngMissingBaseUrl && (
            <p
              style={{
                marginTop: 6,
                marginBottom: 0,
                fontSize: 11,
                color: AMBER_600,
              }}
            >
              {t("Required — without it, search falls back to DuckDuckGo.")}
            </p>
          )}
        </div>
      )}
      {fields.apiKey && (
        <div style={{ gridColumn: "1 / -1" }}>
          <div
            style={{
              marginBottom: 6,
              fontSize: 12,
              color: MUTED,
            }}
          >
            {t("API Key")}
          </div>
          <div style={{ position: "relative" }}>
            <input
              type={showApiKey ? "text" : "password"}
              autoComplete="new-password"
              spellCheck={false}
              className={inputClass}
              style={{ paddingRight: 40, fontFamily: MONO }}
              {...FOCUS_PROPS}
              value={profile.api_key}
              onChange={(e) =>
                updateProfileField(service, "api_key", e.target.value)
              }
              placeholder="sk-..."
              data-testid={`service-api-key-${service}`}
            />
            <button
              type="button"
              onClick={() => setShowApiKey((prev) => !prev)}
              style={{
                position: "absolute",
                right: 4,
                top: "50%",
                transform: "translateY(-50%)",
                borderRadius: 6,
                padding: 6,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                color: MUTED,
                transition: "background-color 0.15s, color 0.15s",
              }}
              {...hoverProps({ backgroundColor: MUTED_BG, color: FG })}
              aria-label={showApiKey ? t("Hide API key") : t("Show API key")}
              title={showApiKey ? t("Hide API key") : t("Show API key")}
              data-testid={`service-api-key-toggle-${service}`}
            >
              {showApiKey ? (
                <EyeInvisibleOutlined style={{ fontSize: 16 }} />
              ) : (
                <EyeOutlined style={{ fontSize: 16 }} />
              )}
            </button>
          </div>
        </div>
      )}
      {!isCodexOAuth && (
        <div
          style={{
            gridColumn: "1 / -1",
            borderRadius: 12,
            border: `1px solid ${borderA(0.6)}`,
            background: "rgba(244, 244, 245, 0.2)",
          }}
        >
          <button
            type="button"
            onClick={() => setExtraOpen((value) => !value)}
            style={{
              display: "flex",
              width: "100%",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              padding: "12px 14px",
              textAlign: "left",
              border: "none",
              background: "transparent",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
            aria-expanded={extraOpen}
            data-testid={`service-extra-toggle-${service}`}
          >
            <span>
              <span
                style={{
                  display: "block",
                  fontSize: 12,
                  fontWeight: 500,
                  color: FG,
                }}
              >
                {t("Extra (optional)")}
              </span>
              <span
                style={{
                  marginTop: 2,
                  display: "block",
                  fontSize: 11,
                  color: MUTED,
                }}
              >
                {service === "search"
                  ? t("API version and proxy")
                  : t("API version and extra request headers")}
              </span>
            </span>
            <DownOutlined
              style={{
                fontSize: 16,
                color: MUTED,
                transition: "transform 0.2s",
                transform: extraOpen ? "rotate(180deg)" : "rotate(0deg)",
              }}
            />
          </button>
          {extraOpen && (
            <div
              style={{
                display: "grid",
                gap: 16,
                borderTop: `1px solid ${borderA(0.6)}`,
                padding: "16px 14px",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              }}
            >
              <div>
                <div
                  style={{
                    marginBottom: 6,
                    fontSize: 12,
                    color: MUTED,
                  }}
                >
                  {t("API Version")}
                </div>
                <input
                  className={inputClass}
                  {...FOCUS_PROPS}
                  value={profile.api_version}
                  onChange={(e) =>
                    updateProfileField(service, "api_version", e.target.value)
                  }
                  placeholder={t("Optional")}
                  data-testid={`service-api-version-${service}`}
                />
              </div>
              {service === "search" ? (
                <div>
                  <div
                    style={{
                      marginBottom: 6,
                      fontSize: 12,
                      color: MUTED,
                    }}
                  >
                    {t("Proxy")}
                  </div>
                  <input
                    className={inputClass}
                    {...FOCUS_PROPS}
                    value={profile.proxy || ""}
                    onChange={(e) =>
                      updateProfileField(service, "proxy", e.target.value)
                    }
                    placeholder={t("http://127.0.0.1:7890 (optional)")}
                    data-testid={`service-proxy-${service}`}
                  />
                </div>
              ) : (
                <div style={{ gridColumn: "1 / -1" }}>
                  <div
                    style={{
                      marginBottom: 6,
                      fontSize: 12,
                      color: MUTED,
                    }}
                  >
                    {t("Extra Headers (JSON)")}
                  </div>
                  <textarea
                    className={inputClass}
                    style={{ minHeight: 84, resize: "vertical" }}
                    {...FOCUS_PROPS}
                    value={stringifyExtraHeaders(profile.extra_headers)}
                    onChange={(e) =>
                      updateProfileField(
                        service,
                        "extra_headers",
                        e.target.value,
                      )
                    }
                    placeholder='{"APP-Code":"your-app-code"}'
                    data-testid={`service-extra-headers-${service}`}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
