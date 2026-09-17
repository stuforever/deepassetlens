/**
 * 复刻自 DeepTutor 原仓 web/components/settings/MinerUEngineSettings.tsx（整件 1:1，批5 5.2）。
 * 替换点：
 * - 去 "use client"；react-i18next 的 t('English') → 直接内联中文
 *   （映射源 web/locales/zh/app.json，全部键均已收录；"OK" 在 zh 表中即为 "OK"）；
 * - "@/components/settings/shared"|"@/components/settings/Toggle" → "./shared"|"./Toggle"；
 *   "@/lib/api" → "../../lib/api"（并行批同步落盘，按名 import）；
 * - Tailwind 类逐项换为内联样式，颜色用原仓语义 var(--xxx, 兜底值) 承载
 *   （与同批 Toggle.tsx 口径一致）；emerald-600→#059669、red-600→#dc2626、
 *   border-red-500/30 → rgba(239,68,68,0.3)、bg-red-500/10 → rgba(239,68,68,0.1)；
 * - 原生 <select>/<option>/<input>/<button> → antd Select/Input/Button，
 *   本地/云端模式切换按钮组 → antd Segmented（结构等价：二选一分段控件）。
 * lucide-react→antd 图标登记：
 *   CheckCircle2 → CheckCircleFilled；XCircle → CloseCircleFilled；
 *   Loader2 → LoadingOutlined（spin）；Save → SaveOutlined。
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button, Input, Segmented, Select } from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  LoadingOutlined,
  SaveOutlined,
} from "@ant-design/icons";

import {
  SettingRow,
  SettingSection,
  inputClass,
  nativeSelectClass,
  selectOptionClass,
} from "./shared";
import { Toggle } from "./Toggle";
import { apiFetch, apiUrl } from "../../lib/api";

type MinerUMode = "local" | "cloud";
type MinerUModelVersion = "pipeline" | "vlm";
type MinerUDownloadSource = "huggingface" | "modelscope";
type MinerUDownloadType = "pipeline" | "vlm" | "all";

const DEFAULT_BASE_URL = "https://mineru.net";
const DEFAULT_HF_ENDPOINT = "https://huggingface.co";
const LANGUAGE_AUTO = "auto";
const TOKEN_MASK = "••••••••••••";
const MODEL_VERSIONS: MinerUModelVersion[] = ["pipeline", "vlm"];
const DOWNLOAD_SOURCES: MinerUDownloadSource[] = ["huggingface", "modelscope"];
const DOWNLOAD_SOURCE_LABELS: Record<MinerUDownloadSource, string> = {
  huggingface: "HuggingFace",
  modelscope: "ModelScope",
};
const DOWNLOAD_TYPES: MinerUDownloadType[] = ["pipeline", "vlm", "all"];

type MinerUSettings = {
  mode: MinerUMode;
  api_base_url: string;
  local_cli_path: string;
  model_download_source: MinerUDownloadSource;
  model_download_endpoint: string;
  model_version: MinerUModelVersion;
  language: string;
  enable_formula: boolean;
  enable_table: boolean;
  is_ocr: boolean;
  allow_local_model_download: boolean;
};

type DownloadStatus = {
  state: "running" | "done" | "failed" | "cancelled" | string;
  lines: string[];
  message: string;
};

type MinerUPayload = {
  settings: MinerUSettings & { version?: number };
  api_token_set: boolean;
  local_cli?: {
    found: boolean;
    command: string;
    path: string;
    source?: "configured" | "path";
  };
};

function normalizeDraft(payload: MinerUPayload): MinerUSettings {
  const s = payload.settings;
  return {
    mode: s.mode === "cloud" ? "cloud" : "local",
    api_base_url: s.api_base_url || "https://mineru.net",
    local_cli_path: s.local_cli_path || "",
    model_download_source:
      s.model_download_source === "modelscope" ? "modelscope" : "huggingface",
    model_download_endpoint: s.model_download_endpoint || "",
    model_version: s.model_version === "vlm" ? "vlm" : "pipeline",
    language: s.language || "auto",
    enable_formula: Boolean(s.enable_formula),
    enable_table: Boolean(s.enable_table),
    is_ocr: Boolean(s.is_ocr),
    allow_local_model_download: Boolean(s.allow_local_model_download),
  };
}

export function MinerUEngineSettings() {
  const [payload, setPayload] = useState<MinerUPayload | null>(null);
  const [draft, setDraft] = useState<MinerUSettings | null>(null);
  // Token is write-only: blank field + "set/not set" hint. Only sent on save
  // when the user actually edits it (tokenTouched).
  const [tokenDraft, setTokenDraft] = useState("");
  const [tokenTouched, setTokenTouched] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [download, setDownload] = useState<DownloadStatus | null>(null);
  const [downloadType, setDownloadType] =
    useState<MinerUDownloadType>("pipeline");
  const [startingDownload, setStartingDownload] = useState(false);
  const downloadCursor = useRef(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await apiFetch(apiUrl("/api/v1/settings/mineru"));
        const data = (await response.json().catch(() => ({}))) as
          | MinerUPayload
          | { detail?: string };
        if (!response.ok) {
          throw new Error(
            "detail" in data && data.detail
              ? data.detail
              : "加载 MinerU 设置失败。",
          );
        }
        if (cancelled) return;
        const next = data as MinerUPayload;
        setPayload(next);
        setDraft(normalizeDraft(next));
        setTokenDraft("");
        setTokenTouched(false);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = useMemo(() => {
    if (!payload || !draft) return false;
    const current = normalizeDraft(payload);
    return (
      tokenTouched ||
      current.mode !== draft.mode ||
      current.api_base_url !== draft.api_base_url ||
      current.local_cli_path !== draft.local_cli_path ||
      current.model_download_source !== draft.model_download_source ||
      current.model_download_endpoint !== draft.model_download_endpoint ||
      current.model_version !== draft.model_version ||
      current.language !== draft.language ||
      current.enable_formula !== draft.enable_formula ||
      current.enable_table !== draft.enable_table ||
      current.is_ocr !== draft.is_ocr ||
      current.allow_local_model_download !== draft.allow_local_model_download
    );
  }, [draft, payload, tokenTouched]);

  function patch(next: Partial<MinerUSettings>) {
    setDraft((current) => (current ? { ...current, ...next } : current));
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setMessage("");
    setTestResult(null);
    try {
      const body: Record<string, unknown> = {
        ...draft,
        api_token: tokenTouched ? tokenDraft : null,
      };
      const response = await apiFetch(apiUrl("/api/v1/settings/mineru"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = (await response.json().catch(() => ({}))) as
        | MinerUPayload
        | { detail?: string };
      if (!response.ok) {
        throw new Error(
          "detail" in data && data.detail
            ? data.detail
            : "保存 MinerU 设置失败。",
        );
      }
      const next = data as MinerUPayload;
      setPayload(next);
      setDraft(normalizeDraft(next));
      setTokenDraft("");
      setTokenTouched(false);
      setMessage("MinerU 设置已保存。");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function testConnection() {
    if (!draft) return;
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        ...draft,
        api_token: tokenTouched ? tokenDraft : null,
      };
      const response = await apiFetch(apiUrl("/api/v1/settings/mineru/test"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = (await response.json().catch(() => ({}))) as {
        ok?: boolean;
        message?: string;
        detail?: string;
      };
      if (!response.ok) {
        throw new Error(data.detail || "连接测试失败。");
      }
      setTestResult({
        ok: Boolean(data.ok),
        message: data.message || (data.ok ? "OK" : "连接测试失败。"),
      });
    } catch (err) {
      setTestResult({
        ok: false,
        message: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setTesting(false);
    }
  }

  // Poll the download job while it runs; the cursor protocol fetches only
  // new log lines each tick.
  useEffect(() => {
    if (download?.state !== "running") return;
    const timer = setInterval(async () => {
      try {
        const response = await apiFetch(
          apiUrl(
            `/api/v1/settings/mineru/models/download/status?cursor=${downloadCursor.current}`,
          ),
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          state?: string;
          lines?: string[];
          next_cursor?: number;
          message?: string;
        };
        downloadCursor.current = data.next_cursor ?? downloadCursor.current;
        setDownload((current) =>
          current
            ? {
                state: data.state || current.state,
                lines: [...current.lines, ...(data.lines || [])].slice(-100),
                message: data.message || "",
              }
            : current,
        );
      } catch {
        // transient network error — keep polling
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [download?.state]);

  async function startDownload() {
    if (!draft) return;
    setStartingDownload(true);
    try {
      const response = await apiFetch(
        apiUrl("/api/v1/settings/mineru/models/download"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model_type: downloadType,
            source: draft.model_download_source,
            endpoint: draft.model_download_endpoint,
            local_cli_path: draft.local_cli_path,
          }),
        },
      );
      const data = (await response.json().catch(() => ({}))) as {
        ok?: boolean;
        message?: string;
        detail?: string;
      };
      if (!response.ok || !data.ok) {
        setDownload({
          state: "failed",
          lines: [],
          message: data.message || data.detail || "下载失败。",
        });
        return;
      }
      downloadCursor.current = 0;
      setDownload({ state: "running", lines: [], message: "" });
    } finally {
      setStartingDownload(false);
    }
  }

  async function cancelDownload() {
    try {
      await apiFetch(apiUrl("/api/v1/settings/mineru/models/download/cancel"), {
        method: "POST",
      });
    } catch {
      // status polling will surface the final state either way
    }
  }

  const tokenSet = payload?.api_token_set ?? false;
  const isCloud = draft?.mode === "cloud";
  const localCli = payload?.local_cli;

  function renderTestControl(label: string) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {testResult && (
          <span
            style={{
              display: "inline-flex",
              maxWidth: "40vw",
              alignItems: "center",
              gap: 4,
              fontSize: 12,
              color: testResult.ok
                ? "var(--emerald-600, #059669)"
                : "var(--red-600, #dc2626)",
            }}
          >
            {testResult.ok ? (
              <CheckCircleFilled style={{ fontSize: 14, flexShrink: 0 }} />
            ) : (
              <CloseCircleFilled style={{ fontSize: 14, flexShrink: 0 }} />
            )}
            {testResult.message}
          </span>
        )}
        <Button size="small" onClick={testConnection} disabled={testing}>
          {label}
        </Button>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 13,
          color: "var(--muted-foreground, #64748b)",
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 16 }} />
        正在加载 MinerU 设置...
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div
        style={{
          marginBottom: 20,
          borderRadius: 12,
          border: "1px solid rgba(239, 68, 68, 0.3)",
          background: "rgba(239, 68, 68, 0.1)",
          padding: "12px 16px",
          fontSize: 13,
          color: "var(--red-600, #dc2626)",
        }}
      >
        {error}
      </div>
    );
  }

  if (!draft) return null;

  return (
    <>
      {error && (
        <div
          style={{
            marginBottom: 20,
            borderRadius: 12,
            border: "1px solid rgba(239, 68, 68, 0.3)",
            background: "rgba(239, 68, 68, 0.1)",
            padding: "12px 16px",
            fontSize: 13,
            color: "var(--red-600, #dc2626)",
          }}
        >
          {error}
        </div>
      )}

      <SettingSection
        title="解析后端"
        description="选择 PDF 解析的运行位置。"
      >
        <SettingRow
          title="模式"
          description={
            isCloud
              ? "文档将上传到 mineru.net 进行解析。"
              : "解析在本机使用本地安装的 MinerU 运行。"
          }
          control={
            <Segmented
              value={draft.mode}
              onChange={(value) => {
                patch({ mode: value as MinerUMode });
                setTestResult(null);
              }}
              options={[
                { label: "本地", value: "local" },
                { label: "云端 API", value: "cloud" },
              ]}
            />
          }
        />
      </SettingSection>

      {!isCloud && (
        <SettingSection
          title="本地安装"
          description="MinerU 命令行需要对 DeepTutor 服务进程可达。建议预留 ≥20 GB 可用磁盘（官方建议）：安装约 2-4 GB，首次解析懒下载约 1-2 GB 模型，另含解析缓存。"
        >
          <SettingRow
            title={
              localCli?.found
                ? "已检测到 MinerU 命令行。"
                : localCli?.source === "configured"
                  ? "配置的 CLI 路径不是可执行文件。"
                  : "未在 PATH 中找到 MinerU 命令行。"
            }
            description={
              localCli?.found
                ? localCli.path
                : "可安装到任意 Python 环境：uv pip install -U \"mineru[core]\" —— 然后在下方填写 CLI 路径；或装进服务端环境由 PATH 自动检测。"
            }
            control={renderTestControl("检测")}
          />
          <SettingRow
            title="CLI 路径"
            description="可选。指向隔离环境（uv tool、pipx、conda）中的 mineru 可执行文件，避免依赖冲突。留空则从 PATH 自动检测。"
            control={
              <Input
                className={inputClass}
                style={{
                  width: 320,
                  maxWidth: "48vw",
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                  fontSize: 12,
                }}
                placeholder="从 PATH 自动检测"
                value={draft.local_cli_path}
                onChange={(e) => patch({ local_cli_path: e.target.value })}
              />
            }
          />
        </SettingSection>
      )}

      {!isCloud && (
        <SettingSection
          title="模型权重"
          description="本地解析需要约 1-2 GB 的模型权重。默认不会自动下载——可在下方显式下载，或允许首次解析时自动下载。"
        >
          <SettingRow
            title="允许自动下载模型"
            description="默认关闭。关闭时，本地解析会给出提示并失败，而不是在首次运行时静默下载数 GB 的权重。开启后首次解析会自动获取模型，或使用下方的显式下载。"
            control={
              <Toggle
                checked={draft.allow_local_model_download}
                onChange={(v) => patch({ allow_local_model_download: v })}
              />
            }
          />
          <SettingRow
            title="下载源"
            description="中国大陆通常使用 ModelScope 更快。"
            control={
              <Select
                className={nativeSelectClass}
                style={{ width: 176 }}
                value={draft.model_download_source}
                onChange={(value) =>
                  patch({
                    model_download_source: value as MinerUDownloadSource,
                  })
                }
              >
                {DOWNLOAD_SOURCES.map((s) => (
                  <Select.Option
                    key={s}
                    className={selectOptionClass}
                    value={s}
                  >
                    {DOWNLOAD_SOURCE_LABELS[s]}
                  </Select.Option>
                ))}
              </Select>
            }
          />
          {draft.model_download_source === "huggingface" && (
            <SettingRow
              title="下载地址"
              description="自定义 HuggingFace 端点或镜像（例如区域镜像站）。留空使用官方地址。"
              control={
                <Input
                  className={inputClass}
                  style={{
                    width: 320,
                    maxWidth: "48vw",
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                    fontSize: 12,
                  }}
                  placeholder={DEFAULT_HF_ENDPOINT}
                  value={draft.model_download_endpoint}
                  onChange={(e) =>
                    patch({ model_download_endpoint: e.target.value })
                  }
                />
              }
            />
          )}
          <SettingRow
            title="下载模型"
            description="在服务端运行 mineru-models-download，使用上方的下载源和地址。"
            control={
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Select
                  className={nativeSelectClass}
                  style={{ width: 112 }}
                  value={downloadType}
                  onChange={(value) =>
                    setDownloadType(value as MinerUDownloadType)
                  }
                  disabled={download?.state === "running"}
                >
                  {DOWNLOAD_TYPES.map((v) => (
                    <Select.Option
                      key={v}
                      className={selectOptionClass}
                      value={v}
                    >
                      {v}
                    </Select.Option>
                  ))}
                </Select>
                {download?.state === "running" ? (
                  <Button size="small" onClick={cancelDownload}>
                    取消
                  </Button>
                ) : (
                  <Button
                    type="primary"
                    size="small"
                    onClick={startDownload}
                    disabled={startingDownload}
                    loading={startingDownload}
                  >
                    下载
                  </Button>
                )}
              </div>
            }
          />
          {download && (
            <div style={{ paddingLeft: 4, paddingRight: 4, paddingBottom: 16 }}>
              <div
                style={{
                  marginBottom: 8,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 12,
                  color:
                    download.state === "done"
                      ? "var(--emerald-600, #059669)"
                      : download.state === "running"
                        ? "var(--muted-foreground, #64748b)"
                        : "var(--red-600, #dc2626)",
                }}
              >
                {download.state === "running" ? (
                  <LoadingOutlined spin style={{ fontSize: 12 }} />
                ) : download.state === "done" ? (
                  <CheckCircleFilled style={{ fontSize: 14 }} />
                ) : (
                  <CloseCircleFilled style={{ fontSize: 14 }} />
                )}
                {download.state === "running"
                  ? "正在下载模型..."
                  : download.message || download.state}
              </div>
              {download.lines.length > 0 && (
                <pre
                  style={{
                    maxHeight: 160,
                    overflowY: "auto",
                    whiteSpace: "pre-wrap",
                    borderRadius: 8,
                    border: "1px solid var(--border, #e5e7eb)",
                    background: "var(--card, #ffffff)",
                    padding: "8px 12px",
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                    fontSize: 11,
                    lineHeight: 1.625,
                    color: "var(--muted-foreground, #64748b)",
                    margin: 0,
                  }}
                >
                  {download.lines.join("\n")}
                </pre>
              )}
            </div>
          )}
        </SettingSection>
      )}

      {isCloud && (
        <SettingSection
          title="云端 API"
          description="在 mineru.net → API 管理中获取 API 令牌。"
        >
          <SettingRow
            title="API 基础地址"
            description="仅在使用自部署 MinerU 端点时才需修改。"
            control={
              <Input
                className={inputClass}
                style={{ width: 320, maxWidth: "48vw" }}
                placeholder={DEFAULT_BASE_URL}
                value={draft.api_base_url}
                onChange={(e) => patch({ api_base_url: e.target.value })}
              />
            }
          />
          <SettingRow
            title="API 令牌"
            description={
              tokenSet
                ? "已保存令牌。输入可替换；留空则保持不变。"
                : "尚未保存令牌。"
            }
            control={
              <Input
                type="password"
                className={inputClass}
                style={{ width: 320, maxWidth: "48vw" }}
                placeholder={tokenSet ? TOKEN_MASK : "粘贴 API 令牌"}
                value={tokenDraft}
                onChange={(e) => {
                  setTokenDraft(e.target.value);
                  setTokenTouched(true);
                }}
              />
            }
          />
          <SettingRow
            title="测试连接"
            description="向 MinerU API 校验令牌（不消耗额度）。"
            control={renderTestControl("测试")}
          />
        </SettingSection>
      )}

      <SettingSection
        title="解析选项"
        description="对每个文档转发给 MinerU。"
      >
        <SettingRow
          title="模型版本"
          description="pipeline 更快；vlm 为视觉语言模型。"
          control={
            <Select
              className={nativeSelectClass}
              style={{ width: 160 }}
              value={draft.model_version}
              onChange={(value) =>
                patch({ model_version: value as MinerUModelVersion })
              }
            >
              {MODEL_VERSIONS.map((v) => (
                <Select.Option key={v} className={selectOptionClass} value={v}>
                  {v}
                </Select.Option>
              ))}
            </Select>
          }
        />
        <SettingRow
          title="语言"
          description={'文档语言提示。使用 "auto" 让 MinerU 自动识别。'}
          control={
            <Input
              className={inputClass}
              style={{ width: 160 }}
              placeholder={LANGUAGE_AUTO}
              value={draft.language}
              onChange={(e) => patch({ language: e.target.value })}
            />
          }
        />
        <SettingRow
          title="提取公式"
          control={
            <Toggle
              checked={draft.enable_formula}
              onChange={(v) => patch({ enable_formula: v })}
            />
          }
        />
        <SettingRow
          title="提取表格"
          control={
            <Toggle
              checked={draft.enable_table}
              onChange={(v) => patch({ enable_table: v })}
            />
          }
        />
        <SettingRow
          title="强制 OCR"
          description="将 PDF 当作扫描图像处理。较慢；仅用于无文本层的 PDF。"
          control={
            <Toggle
              checked={draft.is_ocr}
              onChange={(v) => patch({ is_ocr: v })}
            />
          }
        />
      </SettingSection>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: 12,
            color: "var(--muted-foreground, #64748b)",
          }}
        >
          {message ||
            "MinerU 设置写入 data/user/settings/document_parsing.json。"}
        </p>
        <Button
          type="primary"
          size="small"
          onClick={save}
          disabled={saving || !dirty}
          loading={saving}
          icon={<SaveOutlined />}
        >
          保存 MinerU
        </Button>
      </div>
    </>
  );
}
