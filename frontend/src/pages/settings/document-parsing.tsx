/**
 * 文档解析（1:1 复刻自原仓 web/app/(utility)/settings/document-parsing/page.tsx）：
 * 引擎选择卡（text_only / mineru / docling / markitdown / pymupdf4llm）+
 * 各引擎面板（开关项、就绪徽标、未安装一键 pip 安装、模型一键下载、日志流）。
 * apiFetch/apiUrl → 相对路径 fetch；nativeSelectClass select → antd Select；
 * number input → antd InputNumber；MinerU 面板复用 settings/MinerUEngineSettings。
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, InputNumber, Select, Spin } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, DownloadOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import {
  SettingRow,
  SettingSection,
  SettingsPageHeader,
} from '../../components/settings/shared';
import { MinerUEngineSettings } from '../../components/settings/MinerUEngineSettings';
import { Toggle } from '../../components/settings/Toggle';

type EngineMeta = {
  id: string;
  name: string;
  description: string;
  needs_local_models: boolean;
  available: boolean;
};

type Readiness = { ready: boolean; reason: string; message: string };

type DocumentParsingPayload = {
  engine: string;
  engines: Record<string, Record<string, unknown>>;
  available_engines: EngineMeta[];
  readiness: Record<string, Readiness>;
  installable: string[];
  mineru: { api_token_set: boolean; local_cli?: unknown };
};

const PIP_HINT: Record<string, string> = {
  docling: 'pip install deeptutor[parse-docling]',
  markitdown: 'pip install deeptutor[parse-markitdown]',
  pymupdf4llm: 'pip install deeptutor[parse-pymupdf4llm]',
};

export default function DocumentParsingSettingsPage() {
  const [data, setData] = useState<DocumentParsingPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch('/api/v1/settings/document-parsing');
      const payload = (await response.json().catch(() => ({}))) as
        | DocumentParsingPayload
        | { detail?: string };
      if (!response.ok) {
        throw new Error(
          'detail' in payload && payload.detail
            ? payload.detail
            : '加载文档解析设置失败。',
        );
      }
      setData(payload as DocumentParsingPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const putDocumentParsing = useCallback(
    async (body: Record<string, unknown>) => {
      setBusy(true);
      setError(null);
      try {
        const response = await fetch('/api/v1/settings/document-parsing', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const payload = (await response.json().catch(() => ({}))) as
          | DocumentParsingPayload
          | { detail?: string };
        if (!response.ok) {
          throw new Error(
            'detail' in payload && payload.detail
              ? payload.detail
              : '保存文档解析设置失败。',
          );
        }
        setData(payload as DocumentParsingPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  return (
    <div>
      <SettingsPageHeader
        title="文档解析"
        description="上传的文档如何被转换为文本，供知识库和出题使用。选择一个引擎及其选项。本地模型默认不下载——只有在你显式允许时才会下载。"
      />

      {loading && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
            color: 'rgba(0, 0, 0, 0.45)',
          }}
        >
          <Spin indicator={<LoadingOutlined spin />} />
          加载中…
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            marginBottom: 20,
            borderRadius: 12,
            border: '1px solid rgba(255, 77, 79, 0.3)',
            background: 'rgba(255, 77, 79, 0.1)',
            padding: '12px 16px',
            fontSize: 13,
            color: '#cf1322',
          }}
        >
          {error}
        </div>
      )}

      {!loading && data && (
        <>
          <section style={{ marginBottom: 40 }}>
            <header style={{ marginBottom: 12 }}>
              <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'rgba(0, 0, 0, 0.88)' }}>
                引擎
              </h2>
              <p
                style={{
                  marginTop: 4,
                  marginBottom: 0,
                  fontSize: 12.5,
                  lineHeight: 1.625,
                  color: 'rgba(0, 0, 0, 0.45)',
                }}
              >
                当前引擎负责所有解析。仅文本为内置引擎，只提取纯文本；markitdown 轻量但为可选依赖；MinerU 和 Docling 能产出更丰富结构，但可能需要本地模型或托管 API。
              </p>
            </header>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {data.available_engines.map((engine) => {
                const active = engine.id === data.engine;
                return (
                  <button
                    key={engine.id}
                    type="button"
                    disabled={busy}
                    onClick={() => !active && void putDocumentParsing({ engine: engine.id })}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: 16,
                      borderRadius: 12,
                      padding: '12px 16px',
                      textAlign: 'left',
                      cursor: busy ? 'not-allowed' : 'pointer',
                      opacity: busy ? 0.6 : 1,
                      border: active ? '1px solid rgba(0, 0, 0, 0.88)' : '1px solid #f0f0f0',
                      background: active ? '#fff' : '#fff',
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 13, fontWeight: 500, color: 'rgba(0, 0, 0, 0.88)' }}>
                          {engine.name}
                        </span>
                        {active && (
                          <span
                            style={{
                              borderRadius: 999,
                              background: 'rgba(0, 0, 0, 0.88)',
                              padding: '2px 8px',
                              fontSize: 10,
                              fontWeight: 500,
                              color: '#fff',
                            }}
                          >
                            已激活
                          </span>
                        )}
                        {!engine.available && (
                          <span
                            style={{
                              borderRadius: 999,
                              border: '1px solid #f0f0f0',
                              padding: '2px 8px',
                              fontSize: 10,
                              color: 'rgba(0, 0, 0, 0.45)',
                            }}
                          >
                            未安装
                          </span>
                        )}
                      </div>
                      <p style={{ marginTop: 4, marginBottom: 0, fontSize: 12, color: 'rgba(0, 0, 0, 0.45)' }}>
                        {engine.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {data.engine === 'text_only' && <TextOnlyPanel />}

          {data.engine === 'mineru' && <MinerUEngineSettings />}

          {data.engine === 'docling' && (
            <DoclingPanel
              slice={data.engines.docling || {}}
              readiness={data.readiness.docling}
              available={
                data.available_engines.find((e) => e.id === 'docling')
                  ?.available ?? false
              }
              busy={busy}
              onInstalled={() => void load()}
              onSave={(patch) =>
                void putDocumentParsing({ engines: { docling: patch } })
              }
            />
          )}

          {data.engine === 'markitdown' && (
            <MarkItDownPanel
              slice={data.engines.markitdown || {}}
              available={
                data.available_engines.find((e) => e.id === 'markitdown')
                  ?.available ?? false
              }
              busy={busy}
              onInstalled={() => void load()}
              onSave={(patch) =>
                void putDocumentParsing({ engines: { markitdown: patch } })
              }
            />
          )}

          {data.engine === 'pymupdf4llm' && (
            <PyMuPDF4LLMPanel
              slice={data.engines.pymupdf4llm || {}}
              available={
                data.available_engines.find((e) => e.id === 'pymupdf4llm')
                  ?.available ?? false
              }
              busy={busy}
              onInstalled={() => void load()}
              onSave={(patch) =>
                void putDocumentParsing({ engines: { pymupdf4llm: patch } })
              }
            />
          )}
        </>
      )}
    </div>
  );
}

function TextOnlyPanel() {
  return (
    <SettingSection
      title="仅文本"
      description="内置纯文本提取，支持 PDF、Office 和文本文件。无需可选解析包、模型下载、OCR 或版面重建。"
    >
      <SettingRow
        title="模型状态"
        control={
          <ReadinessBadge
            readiness={{ ready: true, reason: 'ready', message: '' }}
          />
        }
      />
    </SettingSection>
  );
}

function ReadinessBadge({ readiness }: { readiness?: Readiness }) {
  if (!readiness) return null;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 12,
        color: readiness.ready ? '#389e0d' : '#d48806',
      }}
    >
      {readiness.ready ? (
        <CheckCircleOutlined style={{ flexShrink: 0 }} />
      ) : (
        <CloseCircleOutlined style={{ flexShrink: 0 }} />
      )}
      {readiness.ready ? '已就绪，可解析。' : readiness.message}
    </span>
  );
}

// Full-width readiness line for engines whose "not ready" guidance is a
// multi-sentence message (e.g. Docling's "models not downloaded" hint). A long
// message must wrap full-width — it doesn't fit a SettingRow's compact,
// non-shrinking control slot (which overflows and squeezes the title).
function ReadinessNotice({ readiness }: { readiness?: Readiness }) {
  if (!readiness) return null;
  if (readiness.ready) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '16px 4px',
          fontSize: 12,
          color: '#389e0d',
        }}
      >
        <CheckCircleOutlined style={{ flexShrink: 0 }} />
        已就绪，可解析。
      </div>
    );
  }
  return (
    <div style={{ padding: '16px 4px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          borderRadius: 8,
          border: '1px solid rgba(250, 173, 20, 0.3)',
          background: 'rgba(250, 173, 20, 0.1)',
          padding: '10px 12px',
          fontSize: 12,
          lineHeight: 1.625,
          color: '#d48806',
        }}
      >
        <CloseCircleOutlined style={{ marginTop: 2, flexShrink: 0 }} />
        <span style={{ minWidth: 0 }}>{readiness.message}</span>
      </div>
    </div>
  );
}

function DoclingPanel({
  slice,
  readiness,
  available,
  busy,
  onInstalled,
  onSave,
}: {
  slice: Record<string, unknown>;
  readiness?: Readiness;
  available: boolean;
  busy: boolean;
  onInstalled: () => void;
  onSave: (patch: Record<string, unknown>) => void;
}) {
  const doOcr = Boolean(slice.do_ocr);
  const doTables = slice.do_table_structure !== false;
  const allowDownload = Boolean(slice.allow_local_model_download);

  if (!available) {
    return (
      <NotInstalledSection
        engineId="docling"
        title="Docling"
        onInstalled={onInstalled}
      />
    );
  }

  return (
    <SettingSection
      title="Docling"
      description="对 PDF/Office/HTML/图片做结构化转换。首次运行会下载版面/表格模型。"
    >
      <ReadinessNotice readiness={readiness} />
      {readiness && !readiness.ready && (
        <ModelDownloadRow
          engineId="docling"
          title="Docling"
          onDownloaded={onInstalled}
        />
      )}
      <SettingRow
        title="允许自动下载模型"
        description="默认关闭。关闭时，解析会给出提示并失败，而不是静默下载模型。也可用 `docling-tools models download` 预先下载。"
        control={
          <Toggle
            checked={allowDownload}
            disabled={busy}
            onChange={(v) => onSave({ allow_local_model_download: v })}
          />
        }
      />
      <SettingRow
        title="识别表格"
        control={
          <Toggle
            checked={doTables}
            disabled={busy}
            onChange={(v) => onSave({ do_table_structure: v })}
          />
        }
      />
      <SettingRow
        title="对扫描页做 OCR"
        description="较慢；仅对纯图片 PDF 启用。"
        control={
          <Toggle
            checked={doOcr}
            disabled={busy}
            onChange={(v) => onSave({ do_ocr: v })}
          />
        }
      />
    </SettingSection>
  );
}

function MarkItDownPanel({
  slice,
  available,
  busy,
  onInstalled,
  onSave,
}: {
  slice: Record<string, unknown>;
  available: boolean;
  busy: boolean;
  onInstalled: () => void;
  onSave: (patch: Record<string, unknown>) => void;
}) {
  const llmImages = Boolean(slice.enable_llm_image_description);

  if (!available) {
    return (
      <NotInstalledSection
        engineId="markitdown"
        title="markitdown"
        onInstalled={onInstalled}
      />
    );
  }

  return (
    <SettingSection
      title="markitdown"
      description="轻量级 Markdown 转换，支持多种格式，无需下载模型。"
    >
      <SettingRow
        title="用视觉模型描述图片"
        description="预留功能 — 转换时用 DeepTutor 的视觉模型为图片生成描述。"
        control={
          <Toggle
            checked={llmImages}
            disabled={busy}
            onChange={(v) => onSave({ enable_llm_image_description: v })}
          />
        }
      />
    </SettingSection>
  );
}

const PYMUPDF4LLM_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'webp'];

function PyMuPDF4LLMPanel({
  slice,
  available,
  busy,
  onInstalled,
  onSave,
}: {
  slice: Record<string, unknown>;
  available: boolean;
  busy: boolean;
  onInstalled: () => void;
  onSave: (patch: Record<string, unknown>) => void;
}) {
  const writeImages = slice.write_images !== false;
  const imageFormat =
    typeof slice.image_format === 'string' ? slice.image_format : 'png';
  const imageDpi = typeof slice.image_dpi === 'number' ? slice.image_dpi : 150;

  if (!available) {
    return (
      <NotInstalledSection
        engineId="pymupdf4llm"
        title="PyMuPDF4LLM"
        onInstalled={onInstalled}
      />
    );
  }

  return (
    <SettingSection
      title="PyMuPDF4LLM"
      description="Lightweight PDF/e-book → Markdown built on PyMuPDF. No model downloads or CUDA, so it runs on low-end machines."
    >
      <SettingRow
        title="Extract images"
        description="Save embedded images and rendered vector graphics into the parse, referenced from the Markdown."
        control={
          <Toggle
            checked={writeImages}
            disabled={busy}
            onChange={(v) => onSave({ write_images: v })}
          />
        }
      />
      {writeImages && (
        <>
          <SettingRow
            title="Image format"
            control={
              <Select
                style={{ width: 112 }}
                value={imageFormat}
                disabled={busy}
                onChange={(v) => onSave({ image_format: v })}
                options={PYMUPDF4LLM_IMAGE_FORMATS.map((f) => ({
                  value: f,
                  label: f,
                }))}
              />
            }
          />
          <SettingRow
            title="Image resolution (DPI)"
            description="Higher is sharper but larger. 72–600."
            control={
              <InputNumber
                min={72}
                max={600}
                step={1}
                value={imageDpi}
                disabled={busy}
                onChange={(v) => {
                  if (typeof v === 'number' && Number.isFinite(v)) {
                    onSave({ image_dpi: v });
                  }
                }}
                style={{ width: 96 }}
              />
            }
          />
        </>
      )}
    </SettingSection>
  );
}

type JobKind = 'install' | 'models';

type JobStatus = {
  state: 'running' | 'done' | 'failed' | 'cancelled' | string;
  kind: JobKind;
  lines: string[];
  message: string;
};

// Shared driver for the page's one-click background jobs (pip install / model
// download). Mirrors the MinerU model-download UI: POST to start → poll a shared
// cursor-based log filtered by `kind` → call onDone once on success. Only one
// job runs server-side at a time, so the kind filter keeps each card's view to
// its own job.
function useBackgroundJob(
  kind: JobKind,
  startUrl: string,
  engineId: string,
  onDone: () => void,
) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const cursor = useRef(0);
  const notifiedDone = useRef(false);

  useEffect(() => {
    if (job?.state !== 'running') return;
    const timer = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/v1/settings/document-parsing/job/status?cursor=${cursor.current}`,
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          state?: string;
          kind?: string;
          lines?: string[];
          next_cursor?: number;
          message?: string;
        };
        // A different kind of job is running — leave our view alone.
        if (data.kind && data.kind !== kind) return;
        cursor.current = data.next_cursor ?? cursor.current;
        setJob((current) =>
          current
            ? {
                state: data.state || current.state,
                kind,
                lines: [...current.lines, ...(data.lines || [])].slice(-100),
                message: data.message || '',
              }
            : current,
        );
        if (data.state === 'done' && !notifiedDone.current) {
          notifiedDone.current = true;
          onDone();
        }
      } catch {
        // transient network error — keep polling
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [job?.state, kind, onDone]);

  async function start() {
    setStarting(true);
    notifiedDone.current = false;
    try {
      const response = await fetch(startUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine: engineId }),
      });
      const data = (await response.json().catch(() => ({}))) as {
        ok?: boolean;
        message?: string;
        detail?: string;
      };
      if (!response.ok || !data.ok) {
        setJob({
          state: 'failed',
          kind,
          lines: [],
          message: data.message || data.detail || 'Failed.',
        });
        return;
      }
      cursor.current = 0;
      setJob({ state: 'running', kind, lines: [], message: '' });
    } finally {
      setStarting(false);
    }
  }

  async function cancel() {
    try {
      await fetch('/api/v1/settings/document-parsing/job/cancel', {
        method: 'POST',
      });
    } catch {
      // status polling surfaces the final state either way
    }
  }

  return { job, starting, start, cancel };
}

// Status line + streamed log for a background job, shared by install / download.
function JobLog({
  job,
  runningLabel,
  doneLabel,
}: {
  job: JobStatus | null;
  runningLabel: string;
  doneLabel: string;
}) {
  if (!job) return null;
  return (
    <div style={{ padding: '0 4px 4px' }}>
      <div
        style={{
          marginBottom: 8,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 12,
          color:
            job.state === 'done'
              ? '#389e0d'
              : job.state === 'running'
                ? 'rgba(0, 0, 0, 0.45)'
                : '#cf1322',
        }}
      >
        {job.state === 'running' ? (
          <LoadingOutlined spin style={{ fontSize: 12 }} />
        ) : job.state === 'done' ? (
          <CheckCircleOutlined />
        ) : (
          <CloseCircleOutlined />
        )}
        {job.state === 'running'
          ? runningLabel
          : job.state === 'done'
            ? doneLabel
            : job.message || job.state}
      </div>
      {job.lines.length > 0 && (
        <pre
          style={{
            maxHeight: 160,
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            borderRadius: 8,
            border: '1px solid rgba(0, 0, 0, 0.06)',
            background: 'rgba(0, 0, 0, 0.02)',
            padding: '8px 12px',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
            fontSize: 11,
            lineHeight: 1.625,
            color: 'rgba(0, 0, 0, 0.45)',
            margin: 0,
          }}
        >
          {job.lines.join('\n')}
        </pre>
      )}
    </div>
  );
}

function JobButton({
  running,
  starting,
  label,
  onStart,
  onCancel,
}: {
  running: boolean;
  starting: boolean;
  label: string;
  onStart: () => void;
  onCancel: () => void;
}) {
  if (running) {
    return (
      <Button onClick={onCancel} style={{ flexShrink: 0 }}>
        取消
      </Button>
    );
  }
  return (
    <Button
      type="primary"
      onClick={onStart}
      disabled={starting}
      icon={starting ? <LoadingOutlined spin /> : <DownloadOutlined />}
      style={{ flexShrink: 0 }}
    >
      {label}
    </Button>
  );
}

// The active engine's panel when its optional package isn't installed: a clean
// section with the pip hint and a one-click installer. Keeps install in ONE
// place per engine; reloads on success so the engine flips to available.
function NotInstalledSection({
  engineId,
  title,
  onInstalled,
}: {
  engineId: string;
  title: string;
  onInstalled: () => void;
}) {
  const { job, starting, start, cancel } = useBackgroundJob(
    'install',
    '/api/v1/settings/document-parsing/install',
    engineId,
    onInstalled,
  );

  return (
    <SettingSection
      title={title}
      description="Not installed yet. Install the package to use this engine — runs on the server, no terminal needed."
    >
      <SettingRow
        title="Install package"
        description={PIP_HINT[engineId]}
        control={
          <JobButton
            running={job?.state === 'running'}
            starting={starting}
            label="Download & install"
            onStart={() => void start()}
            onCancel={() => void cancel()}
          />
        }
      />
      <JobLog
        job={job}
        runningLabel={`Installing ${title}…`}
        doneLabel="Installed. Reloading…"
      />
    </SettingSection>
  );
}

// One-click model-weight download for an installed engine that still needs its
// models (e.g. Docling). Mirrors MinerU's "Download models"; reloads readiness
// on success so the gate clears.
function ModelDownloadRow({
  engineId,
  title,
  onDownloaded,
}: {
  engineId: string;
  title: string;
  onDownloaded: () => void;
}) {
  const { job, starting, start, cancel } = useBackgroundJob(
    'models',
    '/api/v1/settings/document-parsing/models/download',
    engineId,
    onDownloaded,
  );

  return (
    <>
      <SettingRow
        title="下载模型"
        description="Fetch the model weights onto the server now — no terminal needed."
        control={
          <JobButton
            running={job?.state === 'running'}
            starting={starting}
            label="下载模型"
            onStart={() => void start()}
            onCancel={() => void cancel()}
          />
        }
      />
      <JobLog
        job={job}
        runningLabel={`Downloading ${title} models…`}
        doneLabel="Downloaded. Reloading…"
      />
    </>
  );
}
