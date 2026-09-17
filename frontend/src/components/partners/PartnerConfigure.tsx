/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerConfigure.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover/focus 用事件直写；源内重复 4 次的主色保存按钮等价抽出为
 * 局部 PrimaryActionButton，文案/样式/禁用态逐字一致；响应式 sm:grid-cols-2 直接
 * 取桌面两列）；hover:bg-[var(--muted)] hover:text-red-500 以事件直写。
 * lucide-react→antd 图标登记：Loader2 → LoadingOutlined(spin)；Plus → PlusOutlined；
 * Save → SaveOutlined；Trash2 → DeleteOutlined；X → CloseOutlined。
 *
 * Partner configuration panel: identity, soul, model, tool surface, and the
 * provisioned asset library (knowledge bases / skills / notebooks copied
 * into the partner workspace).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CloseOutlined,
  DeleteOutlined,
  LoadingOutlined,
  PlusOutlined,
  SaveOutlined,
} from "@ant-design/icons";
import PartnerModelSelect from "./PartnerModelSelect";
import { listLLMOptions, type LLMOption } from "../../lib/llm-options";
import type { LLMSelection } from "../../lib/unified-ws";
import {
  addPartnerAssets,
  getPartnerAssets,
  getPartnerSoul,
  getToolOptions,
  removePartnerAsset,
  savePartnerSoul,
  updatePartner,
  type PartnerAssets,
  type PartnerInfo,
  type ToolOptions,
} from "../../lib/partners-api";
import AssetPicker, {
  type AssetSelection,
} from "./AssetPicker";
import ToolPicker from "./ToolPicker";
import FaceEditor, { type FaceValue } from "./FaceEditor";
import SoulEditor from "./SoulEditor";

const ZH_MESSAGES: Record<string, string> = {
  Saved: "已保存",
  "Save failed": "保存失败",
  "Soul saved": "灵魂已保存",
  "Model updated — applies from the next message":
    "模型已更新——下一条消息起生效",
  "Tools updated — applies from the next message": "工具已更新——下一条消息起生效",
  "Some items failed: {{names}}": "部分内容失败：{{names}}",
  "Assets added": "已添加到资料库",
  "Copy into workspace": "复制进工作区",
  "Remove failed": "移除失败",
  "Knowledge base": "知识库",
  Skill: "技能",
  Notebook: "笔记本",
  Identity: "身份",
  Name: "名称",
  "Reply language": "回复语言",
  "Auto (English)": "自动（英文）",
  Description: "描述",
  Face: "形象",
  Soul: "灵魂",
  "The partner's persona — injected into every conversation.":
    "伙伴的人格设定——注入每一次对话。",
  Model: "模型",
  "The primary model answers every turn; if it fails outright, the turn is retried once on the backup.":
    "主模型负责每一轮回答；当它彻底失败时，会用备用模型重试一次。",
  "Primary model": "主模型",
  "System default": "系统默认",
  "Backup model": "备用模型",
  "No backup": "不设备用",
  "Failed turns are not retried.": "失败的轮次不会重试。",
  Tools: "工具",
  "What this partner is allowed to use.": "该伙伴被允许使用的能力。",
  Library: "资料库",
  "Knowledge bases, skills, and notebooks copied into this partner's workspace.":
    "已复制进该伙伴工作区的知识库、技能与笔记本。",
  Cancel: "取消",
  Add: "添加",
  "Nothing assigned yet — this partner only knows what you tell it.":
    "还没有分配任何内容——这个伙伴只知道你告诉它的事。",
  Remove: "移除",
  Save: "保存",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

function Section({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section
      style={{
        borderRadius: 12,
        border: "1px solid var(--border, #e2e8f0)",
        padding: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <div>
          <h3
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "var(--foreground, #0f172a)",
              margin: 0,
            }}
          >
            {title}
          </h3>
          {description && (
            <p
              style={{
                marginTop: 2,
                fontSize: 11.5,
                color: "var(--muted-foreground, #64748b)",
                margin: "2px 0 0",
              }}
            >
              {description}
            </p>
          )}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

/** 源内重复 4 次的主色保存按钮（文案/图标/禁用态逐字一致，等价抽出）。 */
function PrimaryActionButton({
  busy,
  disabled,
  onClick,
  label,
}: {
  busy: boolean;
  disabled?: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        borderRadius: 8,
        border: "none",
        background: "var(--primary, #2563eb)",
        padding: "6px 12px",
        fontSize: 12,
        fontWeight: 500,
        color: "var(--primary-foreground, #ffffff)",
        cursor: "pointer",
        opacity: disabled ? 0.4 : 1,
      }}
    >
      {busy ? (
        <LoadingOutlined spin style={{ fontSize: 14 }} />
      ) : (
        <SaveOutlined style={{ fontSize: 14 }} />
      )}
      {label}
    </button>
  );
}

export default function PartnerConfigure({
  partner,
  onToast,
  onUpdated,
}: {
  partner: PartnerInfo;
  onToast: (msg: string) => void;
  onUpdated: () => void;
}) {
  const partnerId = partner.partner_id;

  // Identity
  const [name, setName] = useState(partner.name);
  const [description, setDescription] = useState(partner.description ?? "");
  const [face, setFace] = useState<FaceValue>({
    emoji: partner.emoji ?? "",
    color: partner.color ?? "",
    avatar: partner.avatar ?? "",
  });
  const [language, setLanguage] = useState(partner.language ?? "");
  const [savingIdentity, setSavingIdentity] = useState(false);

  // Soul
  const [soul, setSoul] = useState("");
  const [soulLoaded, setSoulLoaded] = useState(false);
  const [savingSoul, setSavingSoul] = useState(false);

  // Model
  const [llmOptions, setLLMOptions] = useState<LLMOption[]>([]);
  const [activeLLMDefault, setActiveLLMDefault] = useState<LLMSelection | null>(
    null,
  );
  const [llmLoading, setLLMLoading] = useState(true);
  const [llmError, setLLMError] = useState(false);
  const [selection, setSelection] = useState<LLMSelection | null>(
    partner.llm_selection ?? null,
  );
  const [backupSelection, setBackupSelection] = useState<LLMSelection | null>(
    partner.backup_llm_selection ?? null,
  );

  // Tools
  const [toolOptions, setToolOptions] = useState<ToolOptions | null>(null);
  const [enabledTools, setEnabledTools] = useState<string[]>([]);
  const [builtinTools, setBuiltinTools] = useState<string[]>([]);
  const [mcpTools, setMcpTools] = useState<string[]>([]);
  const [savingTools, setSavingTools] = useState(false);

  // Assets
  const [assets, setAssets] = useState<PartnerAssets | null>(null);
  const [showAssetPicker, setShowAssetPicker] = useState(false);
  const [pendingAssets, setPendingAssets] = useState<AssetSelection>({
    knowledge_bases: [],
    skills: [],
    notebooks: [],
  });
  const [addingAssets, setAddingAssets] = useState(false);

  // 局部 hover/focus 态（Tailwind hover:/focus: 的事件直写承载）
  const [nameFocused, setNameFocused] = useState(false);
  const [descFocused, setDescFocused] = useState(false);
  const [langFocused, setLangFocused] = useState(false);
  const [assetToggleHover, setAssetToggleHover] = useState(false);
  const [assetAddHover, setAssetAddHover] = useState(false);
  const [hoveredAssetRow, setHoveredAssetRow] = useState<string | null>(null);

  useEffect(() => {
    void getPartnerSoul(partnerId)
      .then((content) => {
        setSoul(content);
        setSoulLoaded(true);
      })
      .catch(() => setSoulLoaded(true));
    void getPartnerAssets(partnerId)
      .then(setAssets)
      .catch(() => {});
    void (async () => {
      try {
        const payload = await listLLMOptions();
        setLLMOptions(payload.options);
        setActiveLLMDefault(payload.active);
        setLLMError(false);
      } catch {
        setLLMError(true);
      } finally {
        setLLMLoading(false);
      }
    })();
    void getToolOptions()
      .then((options) => {
        setToolOptions(options);
        setEnabledTools(
          partner.enabled_tools ?? options.tools.map((tool) => tool.name),
        );
        setBuiltinTools(
          partner.builtin_tools ??
            options.builtin_tools.map((tool) => tool.name),
        );
        // MCP is deny-by-default. A nullish value must not materialise as
        // "all selected": the picker hands back exactly what is checked, so
        // that fallback would re-grant every configured MCP tool on save.
        setMcpTools(partner.mcp_tools ?? []);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partnerId]);

  const saveIdentity = async () => {
    setSavingIdentity(true);
    try {
      await updatePartner(partnerId, {
        name,
        description,
        emoji: face.emoji,
        color: face.color,
        avatar: face.avatar,
        language,
      });
      onToast(t("Saved"));
      onUpdated();
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setSavingIdentity(false);
    }
  };

  const saveSoul = async () => {
    setSavingSoul(true);
    try {
      await savePartnerSoul(partnerId, soul);
      onToast(t("Soul saved"));
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setSavingSoul(false);
    }
  };

  const saveModel = async (next: LLMSelection | null) => {
    setSelection(next);
    try {
      await updatePartner(partnerId, { llm_selection: next });
      onToast(t("Model updated — applies from the next message"));
      onUpdated();
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Save failed"));
    }
  };

  const saveBackupModel = async (next: LLMSelection | null) => {
    setBackupSelection(next);
    try {
      await updatePartner(partnerId, { backup_llm_selection: next });
      onToast(t("Model updated — applies from the next message"));
      onUpdated();
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Save failed"));
    }
  };

  const saveTools = async () => {
    setSavingTools(true);
    try {
      await updatePartner(partnerId, {
        enabled_tools: enabledTools,
        builtin_tools: builtinTools,
        mcp_tools: mcpTools,
      });
      onToast(t("Tools updated — applies from the next message"));
      onUpdated();
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setSavingTools(false);
    }
  };

  const submitAssets = async () => {
    setAddingAssets(true);
    try {
      const result = await addPartnerAssets(partnerId, pendingAssets);
      setAssets(result.assets);
      if (result.errors.length > 0) {
        onToast(
          t("Some items failed: {{names}}", {
            names: result.errors.map((e) => e.name).join(", "),
          }),
        );
      } else {
        onToast(t("Assets added"));
      }
      setPendingAssets({ knowledge_bases: [], skills: [], notebooks: [] });
      setShowAssetPicker(false);
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setAddingAssets(false);
    }
  };

  const removeAsset = useCallback(
    async (assetType: "knowledge_base" | "skill" | "notebook", id: string) => {
      try {
        const result = await removePartnerAsset(partnerId, assetType, id);
        setAssets(result.assets);
      } catch (e) {
        onToast(e instanceof Error ? e.message : t("Remove failed"));
      }
    },
    [partnerId, onToast, t],
  );

  const assetRows = useMemo(() => {
    if (!assets) return [];
    return [
      ...assets.knowledge_bases.map((kb) => ({
        type: "knowledge_base" as const,
        id: kb.name,
        label: kb.name,
        kind: t("Knowledge base"),
      })),
      ...assets.skills.map((skill) => ({
        type: "skill" as const,
        id: skill.name,
        label: skill.name,
        kind: t("Skill"),
      })),
      ...assets.notebooks.map((nb) => ({
        type: "notebook" as const,
        id: nb.id,
        label: nb.name || nb.id,
        kind: t("Notebook"),
      })),
    ];
  }, [assets, t]);

  const pendingCount =
    pendingAssets.knowledge_bases.length +
    pendingAssets.skills.length +
    pendingAssets.notebooks.length;

  const fieldBorder = (focused: boolean) =>
    `1px solid ${
      focused ? "var(--ring, #2563eb)" : "var(--border, #e2e8f0)"
    }`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Section
        title={t("Identity")}
        action={
          <PrimaryActionButton
            busy={savingIdentity}
            disabled={savingIdentity || !name.trim()}
            onClick={() => void saveIdentity()}
            label={t("Save")}
          />
        }
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 12,
          }}
        >
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {t("Name")}
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onFocus={() => setNameFocused(true)}
              onBlur={() => setNameFocused(false)}
              style={{
                width: "100%",
                borderRadius: 8,
                border: fieldBorder(nameFocused),
                background: "transparent",
                padding: "6px 12px",
                fontSize: 13,
                outline: "none",
                transition: "border-color 150ms",
              }}
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {t("Reply language")}
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              onFocus={() => setLangFocused(true)}
              onBlur={() => setLangFocused(false)}
              style={{
                width: "100%",
                borderRadius: 8,
                border: fieldBorder(langFocused),
                background: "transparent",
                padding: "6px 12px",
                fontSize: 13,
                outline: "none",
                cursor: "pointer",
                transition: "border-color 150ms",
              }}
            >
              <option value="">{t("Auto (English)")}</option>
              <option value="en">English</option>
              <option value="zh">中文</option>
            </select>
          </div>
          <div style={{ gridColumn: "span 2 / span 2" }}>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {t("Description")}
            </label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onFocus={() => setDescFocused(true)}
              onBlur={() => setDescFocused(false)}
              style={{
                width: "100%",
                borderRadius: 8,
                border: fieldBorder(descFocused),
                background: "transparent",
                padding: "6px 12px",
                fontSize: 13,
                outline: "none",
                transition: "border-color 150ms",
              }}
            />
          </div>
          <div style={{ gridColumn: "span 2 / span 2", marginTop: 4 }}>
            <span
              style={{
                display: "block",
                marginBottom: 8,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {t("Face")}
            </span>
            <FaceEditor name={name} value={face} onChange={setFace} />
          </div>
        </div>
      </Section>

      <Section
        title={t("Soul")}
        description={t(
          "The partner's persona — injected into every conversation.",
        )}
        action={
          <PrimaryActionButton
            busy={savingSoul}
            disabled={savingSoul || !soulLoaded}
            onClick={() => void saveSoul()}
            label={t("Save")}
          />
        }
      >
        <SoulEditor value={soul} onChange={setSoul} heightClass="h-[280px]" />
      </Section>

      <Section
        title={t("Model")}
        description={t(
          "The primary model answers every turn; if it fails outright, the turn is retried once on the backup.",
        )}
      >
        <div
          style={{
            maxWidth: 448,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {t("Primary model")}
            </label>
            <PartnerModelSelect
              options={llmOptions}
              activeDefault={activeLLMDefault}
              value={selection}
              loading={llmLoading}
              error={llmError}
              noneLabel={t("System default")}
              onChange={(next) => void saveModel(next)}
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {t("Backup model")}
            </label>
            <PartnerModelSelect
              options={llmOptions}
              activeDefault={activeLLMDefault}
              value={backupSelection}
              loading={llmLoading}
              error={llmError}
              noneLabel={t("No backup")}
              noneDetail={t("Failed turns are not retried.")}
              onChange={(next) => void saveBackupModel(next)}
            />
          </div>
        </div>
      </Section>

      <Section
        title={t("Tools")}
        description={t("What this partner is allowed to use.")}
        action={
          <PrimaryActionButton
            busy={savingTools}
            disabled={savingTools || !toolOptions}
            onClick={() => void saveTools()}
            label={t("Save")}
          />
        }
      >
        <ToolPicker
          options={toolOptions}
          enabledTools={enabledTools}
          builtinTools={builtinTools}
          mcpTools={mcpTools}
          onChangeEnabledTools={setEnabledTools}
          onChangeBuiltinTools={setBuiltinTools}
          onChangeMcpTools={setMcpTools}
        />
      </Section>

      <Section
        title={t("Library")}
        description={t(
          "Knowledge bases, skills, and notebooks copied into this partner's workspace.",
        )}
        action={
          <button
            type="button"
            onClick={() => setShowAssetPicker((v) => !v)}
            onMouseEnter={() => setAssetToggleHover(true)}
            onMouseLeave={() => setAssetToggleHover(false)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              border: `1px solid ${
                assetToggleHover
                  ? "var(--ring, #2563eb)"
                  : "var(--border, #e2e8f0)"
              }`,
              padding: "6px 12px",
              fontSize: 12,
              fontWeight: 500,
              color: "var(--foreground, #0f172a)",
              background: "transparent",
              cursor: "pointer",
              transition: "border-color 150ms",
            }}
          >
            {showAssetPicker ? (
              <CloseOutlined style={{ fontSize: 14 }} />
            ) : (
              <PlusOutlined style={{ fontSize: 14 }} />
            )}
            {showAssetPicker ? t("Cancel") : t("Add")}
          </button>
        }
      >
        {showAssetPicker && (
          <div
            style={{
              marginBottom: 16,
              borderRadius: 12,
              border: "1px dashed var(--border, #e2e8f0)",
              padding: 14,
            }}
          >
            <AssetPicker
              value={pendingAssets}
              onChange={setPendingAssets}
              excluded={{
                knowledge_bases:
                  assets?.knowledge_bases.map((kb) => kb.name) ?? [],
                skills: assets?.skills.map((skill) => skill.name) ?? [],
                notebooks: assets?.notebooks.map((nb) => nb.id) ?? [],
              }}
            />
            <button
              type="button"
              onClick={() => void submitAssets()}
              onMouseEnter={() => setAssetAddHover(true)}
              onMouseLeave={() => setAssetAddHover(false)}
              disabled={addingAssets || pendingCount === 0}
              style={{
                marginTop: 12,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                border: "none",
                background: "var(--primary, #2563eb)",
                padding: "6px 12px",
                fontSize: 12,
                fontWeight: 500,
                color: "var(--primary-foreground, #ffffff)",
                cursor: "pointer",
                opacity: addingAssets || pendingCount === 0 ? 0.4 : 1,
              }}
            >
              {addingAssets ? (
                <LoadingOutlined spin style={{ fontSize: 14 }} />
              ) : (
                <PlusOutlined style={{ fontSize: 14 }} />
              )}
              {t("Copy into workspace")}
              {pendingCount > 0 ? ` (${pendingCount})` : ""}
            </button>
          </div>
        )}

        {assetRows.length === 0 ? (
          <p
            style={{
              fontSize: 12.5,
              color: "var(--muted-foreground, #64748b)",
              margin: 0,
            }}
          >
            {t(
              "Nothing assigned yet — this partner only knows what you tell it.",
            )}
          </p>
        ) : (
          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
            }}
          >
            {assetRows.map((row, index) => {
              const key = `${row.type}:${row.id}`;
              const hovered = hoveredAssetRow === key;
              return (
                <li
                  key={key}
                  onMouseEnter={() => setHoveredAssetRow(key)}
                  onMouseLeave={() => setHoveredAssetRow(null)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "6px 0",
                    borderTop:
                      index > 0
                        ? "1px solid var(--border, #e2e8f0)"
                        : undefined,
                  }}
                >
                  <span
                    style={{
                      minWidth: 0,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      fontSize: 13,
                      color: "var(--foreground, #0f172a)",
                    }}
                  >
                    {row.label}
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 11,
                        color: "var(--muted-foreground, #64748b)",
                      }}
                    >
                      {row.kind}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => void removeAsset(row.type, row.id)}
                    style={{
                      borderRadius: 6,
                      border: "none",
                      padding: 6,
                      background: hovered
                        ? "var(--muted, #f1f5f9)"
                        : "transparent",
                      color: hovered
                        ? "#ef4444"
                        : "var(--muted-foreground, #64748b)",
                      cursor: "pointer",
                      transition: "background-color 150ms, color 150ms",
                    }}
                    aria-label={t("Remove")}
                  >
                    <DeleteOutlined style={{ fontSize: 14 }} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Section>
    </div>
  );
}
