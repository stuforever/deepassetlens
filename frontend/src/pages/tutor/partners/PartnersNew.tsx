/**
 * PartnersNew 新建伙伴向导页——原仓 DeepTutor web/app/(workspace)/partners/new/page.tsx（526 行）
 * 1:1 移植（批6 6.3）。tupu 路由 /e/sishu/partners/new。
 *
 * 五步全页向导：身份(Identity) → 灵魂(Soul) → 心智(Mind：主/备模型+工具) → 资料库(Library：资产)
 * → 审阅(Review)。一屏一决策；频道在创建后于伙伴详情「频道」Tab 接入。
 *
 * 页面区块（与源逐块对拍）：
 * 1. 顶栏：返回「伙伴」链接（ArrowLeftOutlined）+ 五步圆点指示器（连接线/序号/完成 CheckOutlined，
 *    可点回跳，禁点未来步）+ 右侧占位；
 * 2. 步体（identity/review 步显示 PartnerAvatar(48) 头像）：标题+副标题（review 标题内插伙伴名）；
 * 3. 身份步：名称（Enter 下一步，placeholder「例如 Ada」）/描述/形象 FaceEditor/回复语言 Select
 *    （自动（英文）/English/中文）；
 * 4. 灵魂步：SoulPicker；
 * 5. 心智步：主模型 PartnerModelPicker + 备用模型 PartnerModelSelect（不设备用/失败的轮次不会重试。）
 *    + ToolPicker（三组回调均置 toolsTouched）；
 * 6. 资料库步：AssetPicker（preselectAllSkills）；
 * 7. 审阅步：7 行摘要 dl（名称/描述/灵魂/模型/备用模型/工具 N 系统工具·M MCP 工具/资料库 将复制 N 项）
 *    + 「创建后即可接入…」提示 + 错误框；
 * 8. 底部操作条：上一步（首步 disabled+invisible）/「继续」或「创建伙伴」（creating 转 LoadingOutlined）。
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；next/navigation useRouter → useNavigate；
 * - 路由映射：/partners → /e/sishu/partners；创建成功 /partners/[id] → /e/sishu/partners/detail?id=X；
 * - lucide → @ant-design/icons：ArrowLeft→ArrowLeftOutlined、ArrowRight→ArrowRightOutlined、
 *   Check→CheckOutlined、Loader2→LoadingOutlined(spin)、Sparkles→ThunderboltOutlined（仓内先例）；
 * - useTranslation t(键) → locales/zh/app.json 中文值逐字直用（"Ready to meet {{name}}?" /
 *   "{{count}} items will be copied" 按值内模板插值等价）；本页键全部收录，无英文保留键；
 * - Tailwind → antd props + 内联样式（CSS 变量带 fallback）；hover:/dark:/animate-fade-in/sm:hidden
 *   变体按先例省略（步进 label 恒显，仅移动端差异）；input/select → antd Input/Select
 *   （px-3.5 py-2.5 → padding 10px/14px、rounded-xl → borderRadius 12）；
 * - @/lib/llm-options → ../../../lib/llm-options（IA批6 6.3 lib 补件 canonical 1:1，导出名逐字一致）；
 *   LLMSelection → ../../../lib/unified-ws（同批 canonical 件）；@/lib/partners-api →
 *   ../../../lib/partners-api（同批 canonical 件）；@/components/partners/* →
 *   ../../../components/partners/*（并行批，按名不自造；pages/tutor/partners/ 距 src/ 三级）。
 * - 交互逐字未改：identity 步名称必填才能继续；工具三列表 untouched 且全选 → 提交 null
 *   （后续新工具自动继承）；mcp_tools 恒显式提交；MCP 默认空选。
 * - 类型显式标注（ToolOption/ToolOptions/next: string[]）：并行批缺件期间参数无法推断，
 *   标注类型与源契约逐字一致（类型擦除，运行时零差异）；模块就位后标注仍成立。
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Input, Select } from "antd";
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CheckOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  listLLMOptions,
  sameLLMSelection,
  type LLMOption,
} from "../../../lib/llm-options";
import type { LLMSelection } from "../../../lib/unified-ws";
import {
  createPartner,
  getToolOptions,
  type SoulSpec,
  type ToolOption,
  type ToolOptions,
} from "../../../lib/partners-api";
import AssetPicker, {
  type AssetSelection,
} from "../../../components/partners/AssetPicker";
import PartnerAvatar from "../../../components/partners/PartnerAvatar";
import FaceEditor, { type FaceValue } from "../../../components/partners/FaceEditor";
import PartnerModelPicker from "../../../components/partners/PartnerModelPicker";
import PartnerModelSelect from "../../../components/partners/PartnerModelSelect";
import SoulPicker from "../../../components/partners/SoulPicker";
import ToolPicker from "../../../components/partners/ToolPicker";

// CSS 变量 + fallback（先例同 NotebookPage）
const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const SECONDARY = "var(--secondary, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const PRIMARY_FG = "var(--primary-foreground, #ffffff)";
const DESTRUCTIVE = "var(--destructive, #ff4d4f)";

type StepKey = "identity" | "soul" | "mind" | "library" | "review";

export default function PartnersNew() {
  const navigate = useNavigate();

  const steps: { key: StepKey; label: string }[] = [
    { key: "identity", label: "身份" },
    { key: "soul", label: "灵魂" },
    { key: "mind", label: "心智" },
    { key: "library", label: "资料库" },
    { key: "review", label: "审阅" },
  ];
  const [stepIndex, setStepIndex] = useState(0);
  const step = steps[stepIndex].key;

  // ── form state ────────────────────────────────────────────────
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [face, setFace] = useState<FaceValue>({
    emoji: "",
    color: "",
    avatar: "",
  });
  const [language, setLanguage] = useState("");
  const [soul, setSoul] = useState<SoulSpec>({ source: "default" });
  const [selection, setSelection] = useState<LLMSelection | null>(null);
  const [backupSelection, setBackupSelection] = useState<LLMSelection | null>(
    null,
  );
  const [assets, setAssets] = useState<AssetSelection>({
    knowledge_bases: [],
    skills: [],
    notebooks: [],
  });

  const [llmOptions, setLLMOptions] = useState<LLMOption[]>([]);
  const [activeLLMDefault, setActiveLLMDefault] = useState<LLMSelection | null>(
    null,
  );
  const [llmLoading, setLLMLoading] = useState(true);
  const [llmError, setLLMError] = useState(false);

  const [toolOptions, setToolOptions] = useState<ToolOptions | null>(null);
  const [enabledTools, setEnabledTools] = useState<string[]>([]);
  const [builtinTools, setBuiltinTools] = useState<string[]>([]);
  const [mcpTools, setMcpTools] = useState<string[]>([]);
  const [toolsTouched, setToolsTouched] = useState(false);

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const payload = await listLLMOptions();
        setLLMOptions(payload.options);
        setActiveLLMDefault(payload.active);
      } catch {
        setLLMError(true);
      } finally {
        setLLMLoading(false);
      }
    })();
    void getToolOptions()
      .then((options: ToolOptions) => {
        setToolOptions(options);
        setEnabledTools(options.tools.map((tool: ToolOption) => tool.name));
        setBuiltinTools(
          options.builtin_tools.map((tool: ToolOption) => tool.name),
        );
        // MCP starts empty: these tools reach host-side capabilities, so a new
        // partner gets them only by an explicit pick here.
        setMcpTools([]);
      })
      .catch(() => {});
  }, []);

  const canContinue = step !== "identity" || Boolean(name.trim());

  const goNext = () => {
    if (!canContinue) return;
    setStepIndex((index) => Math.min(index + 1, steps.length - 1));
  };
  const goBack = () => setStepIndex((index) => Math.max(index - 1, 0));

  const submit = async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const allTools =
        toolOptions?.tools.map((tool: ToolOption) => tool.name) ?? [];
      const allBuiltin =
        toolOptions?.builtin_tools.map((tool: ToolOption) => tool.name) ?? [];
      const result = await createPartner({
        name: name.trim(),
        description: description.trim() || undefined,
        soul,
        llm_selection: selection,
        backup_llm_selection: backupSelection,
        language: language || undefined,
        emoji: face.emoji || undefined,
        color: face.color || undefined,
        avatar: face.avatar || undefined,
        // Untouched = default-everything → persist as null so newly
        // configured tools are picked up automatically later.
        enabled_tools: toolsTouched
          ? enabledTools
          : enabledTools.length === allTools.length
            ? null
            : enabledTools,
        builtin_tools: toolsTouched
          ? builtinTools
          : builtinTools.length === allBuiltin.length
            ? null
            : builtinTools,
        // Never null for MCP: the list stays explicit so a server configured
        // later is not silently inherited by this partner.
        mcp_tools: mcpTools,
        assets,
        start: true,
      });
      // Land in the chat tab — the partner is ready to talk to right away
      // (any provisioning misses are visible on the Configure tab's library).
      // 源 /partners/[id] → tupu 参数路由 /e/sishu/partners/:partnerId（IA批6）
      navigate(`/e/sishu/partners/${encodeURIComponent(result.partner_id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
      setCreating(false);
    }
  };

  // ── review summary helpers ────────────────────────────────────
  const soulSummary = useMemo(() => {
    switch (soul.source) {
      case "library":
        return `灵魂库 · ${soul.id ?? ""}`;
      case "persona":
        return `克隆 Persona · ${soul.id ?? ""}`;
      case "custom":
        return "自己撰写";
      default:
        return "默认灵魂";
    }
  }, [soul]);

  const describeSelection = useMemo(
    () =>
      (candidate: LLMSelection | null, noneText: string): string => {
        if (!candidate) return noneText;
        const option = llmOptions.find((opt) =>
          sameLLMSelection(opt, candidate),
        );
        return option ? option.model_name || option.model : candidate.model_id;
      },
    [llmOptions],
  );
  const modelSummary = describeSelection(selection, "系统默认");
  const backupSummary = describeSelection(backupSelection, "不设备用");

  const assetCount =
    assets.knowledge_bases.length +
    assets.skills.length +
    assets.notebooks.length;

  const stepTitle: Record<StepKey, { title: string; subtitle: string }> = {
    identity: {
      title: "这个伙伴是谁？",
      subtitle: "先取个名字、选个形象——其余以后都能改。",
    },
    soul: {
      title: "赋予它灵魂",
      subtitle: "它是谁。可以从模板开始、克隆一个聊天 Persona，或亲手撰写。",
    },
    mind: {
      title: "塑造它的心智",
      subtitle: "它思考用的模型，以及允许使用的工具。",
    },
    library: {
      title: "交给它一些知识",
      subtitle: "分给它一部分你的知识——会复制进伙伴自己的工作区。",
    },
    review: {
      // t("Ready to meet {{name}}?", { name: name.trim() || t("your partner") })
      title: `准备好见到 ${name.trim() || "你的伙伴"} 了吗？`,
      subtitle: "就快好了——创建前最后确认一下。",
    },
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Top bar: back link + step indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "20px 24px 0",
        }}
      >
        <Link
          to="/e/sishu/partners"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            color: MUTED_FG,
            textDecoration: "none",
          }}
        >
          <ArrowLeftOutlined style={{ fontSize: 16 }} />
          伙伴
        </Link>
        <ol
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            listStyle: "none",
            margin: 0,
            padding: 0,
          }}
        >
          {steps.map(({ key, label }, index) => {
            const circleStyle: React.CSSProperties =
              index === stepIndex
                ? { border: `1px solid ${PRIMARY}`, background: PRIMARY, color: PRIMARY_FG }
                : index < stepIndex
                  ? { border: `1px solid ${PRIMARY}`, color: PRIMARY }
                  : { border: `1px solid ${BORDER}`, color: MUTED_FG };
            return (
              <li key={key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {index > 0 && (
                  <span
                    style={{
                      width: 20,
                      height: 1,
                      // bg-[var(--primary)]/40 → 1px 连接线以 opacity 0.4 等价
                      background: index <= stepIndex ? PRIMARY : BORDER,
                      opacity: index <= stepIndex ? 0.4 : 1,
                    }}
                  />
                )}
                <button
                  type="button"
                  disabled={index > stepIndex}
                  onClick={() => setStepIndex(index)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    background: "none",
                    border: "none",
                    padding: 0,
                    cursor: index > stepIndex ? "default" : "pointer",
                  }}
                  aria-label={label}
                >
                  <span
                    style={{
                      display: "flex",
                      width: 24,
                      height: 24,
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "50%",
                      fontSize: 11,
                      fontWeight: 600,
                      ...circleStyle,
                    }}
                  >
                    {index < stepIndex ? (
                      <CheckOutlined style={{ fontSize: 14 }} />
                    ) : (
                      index + 1
                    )}
                  </span>
                  <span
                    style={{
                      fontSize: 12.5,
                      color: index === stepIndex ? FG : MUTED_FG,
                      fontWeight: index === stepIndex ? 500 : 400,
                    }}
                  >
                    {label}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        <span style={{ width: 64 }} />
      </div>

      {/* Step body */}
      <div style={{ minHeight: 0, flex: 1, overflowY: "auto" }}>
        <div
          key={step}
          style={{
            maxWidth: 672,
            margin: "0 auto",
            width: "100%",
            padding: "40px 24px 32px",
          }}
        >
          <header
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 16,
              marginBottom: 28,
            }}
          >
            {step === "identity" || step === "review" ? (
              <PartnerAvatar
                name={name || "?"}
                emoji={face.emoji}
                color={face.color}
                image={face.avatar}
                size={48}
              />
            ) : null}
            <div>
              <h1
                style={{
                  margin: 0,
                  fontSize: 22,
                  fontWeight: 600,
                  letterSpacing: "-0.01em",
                  color: FG,
                }}
              >
                {stepTitle[step].title}
              </h1>
              <p
                style={{
                  margin: "4px 0 0",
                  fontSize: 13.5,
                  lineHeight: 1.625,
                  color: MUTED_FG,
                }}
              >
                {stepTitle[step].subtitle}
              </p>
            </div>
          </header>

          {step === "identity" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div>
                <label
                  style={{
                    display: "block",
                    marginBottom: 6,
                    fontSize: 13,
                    fontWeight: 500,
                    color: FG,
                  }}
                >
                  名称
                </label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onPressEnter={goNext}
                  placeholder="例如 Ada"
                  autoFocus
                  style={{
                    borderRadius: 12,
                    padding: "10px 14px",
                    fontSize: 14,
                  }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    marginBottom: 6,
                    fontSize: 13,
                    fontWeight: 500,
                    color: FG,
                  }}
                >
                  描述
                </label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="这个伙伴是做什么的？"
                  style={{
                    borderRadius: 12,
                    padding: "10px 14px",
                    fontSize: 14,
                  }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    marginBottom: 8,
                    fontSize: 13,
                    fontWeight: 500,
                    color: FG,
                  }}
                >
                  形象
                </label>
                <FaceEditor name={name} value={face} onChange={setFace} />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    marginBottom: 6,
                    fontSize: 13,
                    fontWeight: 500,
                    color: FG,
                  }}
                >
                  回复语言
                </label>
                <Select
                  value={language}
                  onChange={(value) => setLanguage(value)}
                  style={{ width: 192, borderRadius: 12 }}
                  options={[
                    { value: "", label: "自动（英文）" },
                    { value: "en", label: "English" },
                    { value: "zh", label: "中文" },
                  ]}
                />
              </div>
            </div>
          )}

          {step === "soul" && <SoulPicker value={soul} onChange={setSoul} />}

          {step === "mind" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div>
                <h3
                  style={{
                    marginBottom: 8,
                    fontSize: 13,
                    fontWeight: 500,
                    color: MUTED_FG,
                  }}
                >
                  主模型
                </h3>
                <PartnerModelPicker
                  options={llmOptions}
                  activeDefault={activeLLMDefault}
                  value={selection}
                  loading={llmLoading}
                  error={llmError}
                  onChange={setSelection}
                />
              </div>
              <div>
                <h3
                  style={{
                    marginBottom: 8,
                    fontSize: 13,
                    fontWeight: 500,
                    color: MUTED_FG,
                  }}
                >
                  备用模型
                </h3>
                <PartnerModelSelect
                  options={llmOptions}
                  activeDefault={activeLLMDefault}
                  value={backupSelection}
                  loading={llmLoading}
                  error={llmError}
                  noneLabel="不设备用"
                  noneDetail="失败的轮次不会重试。"
                  onChange={setBackupSelection}
                />
              </div>
              <ToolPicker
                options={toolOptions}
                enabledTools={enabledTools}
                builtinTools={builtinTools}
                mcpTools={mcpTools}
                // next: string[] 显式标注——并行批组件就位前 TS 无法从 props 推断
                onChangeEnabledTools={(next: string[]) => {
                  setToolsTouched(true);
                  setEnabledTools(next);
                }}
                onChangeBuiltinTools={(next: string[]) => {
                  setToolsTouched(true);
                  setBuiltinTools(next);
                }}
                onChangeMcpTools={(next: string[]) => {
                  setToolsTouched(true);
                  setMcpTools(next);
                }}
              />
            </div>
          )}

          {step === "library" && (
            <AssetPicker
              value={assets}
              onChange={setAssets}
              preselectAllSkills
            />
          )}

          {step === "review" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <dl
                style={{
                  margin: 0,
                  borderRadius: 16,
                  border: `1px solid ${BORDER}`,
                }}
              >
                {(
                  [
                    ["名称", name.trim() || "—"],
                    ["描述", description.trim() || "—"],
                    ["灵魂", soulSummary],
                    ["模型", modelSummary],
                    ["备用模型", backupSummary],
                    [
                      "工具",
                      `${enabledTools.length} 系统工具${
                        mcpTools.length
                          ? ` · ${mcpTools.length} MCP 工具`
                          : ""
                      }`,
                    ],
                    [
                      "资料库",
                      assetCount > 0
                        ? `将复制 ${assetCount} 项`
                        : "还没有分配任何内容——这个伙伴只知道你告诉它的事。",
                    ],
                  ] as [string, string][]
                ).map(([label, valueText], index) => (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      gap: 16,
                      padding: "12px 16px",
                      borderTop: index === 0 ? undefined : `1px solid ${BORDER}`,
                    }}
                  >
                    <dt
                      style={{
                        width: 96,
                        flexShrink: 0,
                        fontSize: 12.5,
                        color: MUTED_FG,
                      }}
                    >
                      {label}
                    </dt>
                    <dd
                      style={{
                        margin: 0,
                        minWidth: 0,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontSize: 13.5,
                        color: FG,
                      }}
                    >
                      {valueText}
                    </dd>
                  </div>
                ))}
              </dl>
              <p style={{ margin: 0, fontSize: 12.5, color: MUTED_FG }}>
                创建后即可接入飞书、Telegram、Slack 等频道。
              </p>
              {error && (
                <p
                  style={{
                    margin: 0,
                    borderRadius: 8,
                    border: `1px solid ${DESTRUCTIVE}`,
                    background: SECONDARY,
                    padding: "8px 12px",
                    fontSize: 13,
                    color: DESTRUCTIVE,
                  }}
                >
                  {error}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer actions */}
      <div style={{ borderTop: `1px solid ${BORDER}`, padding: "14px 24px" }}>
        <div
          style={{
            maxWidth: 672,
            margin: "0 auto",
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Button
            type="text"
            onClick={goBack}
            disabled={stepIndex === 0}
            icon={<ArrowLeftOutlined style={{ fontSize: 16 }} />}
            style={{
              visibility: stepIndex === 0 ? "hidden" : "visible",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 12,
              padding: "8px 12px",
              fontSize: 13.5,
              color: MUTED_FG,
            }}
          >
            上一步
          </Button>
          {step === "review" ? (
            <Button
              type="primary"
              onClick={() => void submit()}
              disabled={creating || !name.trim()}
              icon={
                creating ? (
                  <LoadingOutlined spin style={{ fontSize: 16 }} />
                ) : (
                  <ThunderboltOutlined style={{ fontSize: 16 }} />
                )
              }
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                borderRadius: 12,
                padding: "10px 20px",
                height: "auto",
                fontSize: 13.5,
                fontWeight: 500,
              }}
            >
              创建伙伴
            </Button>
          ) : (
            <Button
              type="primary"
              onClick={goNext}
              disabled={!canContinue}
              icon={<ArrowRightOutlined style={{ fontSize: 16 }} />}
              style={{
                display: "inline-flex",
                flexDirection: "row-reverse",
                alignItems: "center",
                gap: 8,
                borderRadius: 12,
                padding: "10px 20px",
                height: "auto",
                fontSize: 13.5,
                fontWeight: 500,
              }}
            >
              继续
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
