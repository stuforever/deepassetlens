/**
 * KbDocumentsSection —— 知识库「添加文档」增量上传工作台（拖放选择、上传按钮、任务实时日志与更新历史）。
 * 1:1 复刻自原仓 DeepTutor web/components/knowledge/KbDocumentsSection.tsx（236 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/knowledge-api|knowledge-helpers"
 *           + "@/hooks/useKnowledgeProgress|useKnowledgeHistory" + "@/components/common/ProcessLogs"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json；
 *    其中 "The last indexing run failed. ..." zh 未收录 → 按原文保留英文）；
 *  - validateFiles 的 t 契约 → 本文件 zhT()（键=英文原文，映射对拍 zh/app.json：
 *    "Unsupported file type"→不支持的文件类型、"This file exceeds the maximum size of {{size}}."
 *    →该文件超过了 {{size}} 的大小限制。、"No extension"→无扩展名）；
 *  - lucide-react → @ant-design/icons 语义就近：Loader2→LoadingOutlined、RefreshCw→SyncOutlined、
 *    Upload→UploadOutlined；
 *  - Tailwind → antd 组件 + 最小内联样式（amber 提示 #fffbeb/#fde68a/#b45309、
 *    red 错误 #fef2f2/#fecaca/#b91c1c、muted 文字 #8c8c8c）；
 *  - import 契约（并行 Agent 同步产出，按名 import）：KnowledgeUploadPolicy→'./knowledge-api'、
 *    kbIsUploadable/kbNeedsReindex/resolveKbStatus/resolveProgressPercent/validateFiles/KnowledgeBase
 *    →'./knowledge-helpers'、TaskState→'./useKnowledgeProgress'、HistoryEntry→'./useKnowledgeHistory'、
 *    ProcessLogs→'./ProcessLogs'、FileDropZone→'./FileDropZone'（props 签名与源一致）、
 *    KbUpdateHistory→'./KbUpdateHistory'。
 * 【③语义迁移——tutor 域知识库】判定 isTutorKb（rag_provider === 'tutor_dt' 或
 * pointer_params.source === 'tutor'，均经 props 传入的 kb 判定）：
 *  - isTutorKb 时不渲染上传卡（标题说明/阻断与错误提示/FileDropZone/上传按钮整体），
 *    替换为诚实处置卡「文档管理（教学域通道）」；
 *  - 其余（任务日志/进度条/更新历史）tutor 行照常渲染。
 * 不变：props 契约（kb/uploadPolicy/task?/history/onClearHistory/onRetry?/onUpload）、
 *       canUpload = uploadable || (isError && !isIndexingHere)、blockedReason 优先级（needsReindex→非 ready）、
 *       canRetry/canSubmit 判定、handleSubmit/handleRetry 时序（finally 复位）、
 *       showTaskLogs 四 kind、任务日志标题映射（创建/重试/重建索引/上传进度）、
 *       进度条 percent 下限 4%、task.error 红 pre、error 态仍允许上传以替换失败文件。
 */
import { useState } from "react";
import { Button, Card, Flex, Progress, Typography } from "antd";
import { LoadingOutlined, SyncOutlined, UploadOutlined } from "@ant-design/icons";
import type { KnowledgeUploadPolicy } from "./knowledge-api";
import {
  kbIsUploadable,
  kbNeedsReindex,
  resolveKbStatus,
  resolveProgressPercent,
  validateFiles,
  type KnowledgeBase,
} from "./knowledge-helpers";
import type { TaskState } from "./useKnowledgeProgress";
import type { HistoryEntry } from "./useKnowledgeHistory";
import ProcessLogs from "./ProcessLogs";
import FileDropZone from "./FileDropZone";
import KbUpdateHistory from "./KbUpdateHistory";

const MUTED = "#8c8c8c";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

/** validateFiles 的 t 契约：键=英文原文，中文映射对拍 zh/app.json；模板插值 {{var}} 本地替换。 */
const ZH: Record<string, string> = {
  "Unsupported file type": "不支持的文件类型",
  "This file exceeds the maximum size of {{size}}.": "该文件超过了 {{size}} 的大小限制。",
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

interface KbDocumentsSectionProps {
  kb: KnowledgeBase;
  uploadPolicy: KnowledgeUploadPolicy;
  task?: TaskState;
  history: HistoryEntry[];
  onClearHistory: () => void;
  onRetry?: () => Promise<void>;
  onUpload: (files: File[]) => Promise<void>;
}

/**
 * The "Add documents" tab. Focused on the incremental-upload flow: drop
 * zone, upload button, live process logs while a task runs, and a list of
 * past update events. The file list and preview live under the separate
 * "Files" tab to keep each surface single-purpose.
 */
export default function KbDocumentsSection({
  kb,
  uploadPolicy,
  task,
  history,
  onClearHistory,
  onRetry,
  onUpload,
}: KbDocumentsSectionProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [retrySubmitting, setRetrySubmitting] = useState(false);

  const uploadable = kbIsUploadable(kb);
  const needsReindex = kbNeedsReindex(kb);
  const status = resolveKbStatus(kb);
  const isError = status === "error";

  // 【③语义迁移】tutor 域知识库：上传/文件树/解析进度由教学域管理，本页只做注册表镜像。
  const isTutorKb = !!(
    kb &&
    ((kb as any).rag_provider === "tutor_dt" ||
      (((kb as any).pointer_params || {}) as any).source === "tutor")
  );

  const isUploadingHere = task?.kind === "upload" && task.executing;
  const isIndexingHere =
    (task?.kind === "reindex" || task?.kind === "retry") && task.executing;
  const isRetryingHere = task?.kind === "retry" && task.executing;

  // An error-state KB is not locked: the user can drop the file(s) that failed
  // (Files tab) and upload replacements here, instead of being forced to
  // delete and rebuild the whole base. Uploads stay open unless a rebuild is
  // actively running; legacy/transition states remain genuinely blocked.
  const canUpload = uploadable || (isError && !isIndexingHere);

  const blockedReason = canUpload
    ? null
    : needsReindex
      ? "该知识库使用旧版索引格式，需要重新索引后才能上传。"
      : status !== "ready"
        ? `该知识库当前处于${status.replaceAll("_", " ")}状态，暂时无法上传。`
        : null;

  const selection = validateFiles(files, uploadPolicy, zhT);
  const canRetry = Boolean(onRetry) && isError && !isIndexingHere;
  // Unsupported files are skipped (shown in the drop zone), not blocking, so a
  // picked folder with mixed content still uploads its supported members.
  const canSubmit =
    canUpload &&
    selection.validFiles.length > 0 &&
    !submitting &&
    !isUploadingHere;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await onUpload(selection.validFiles);
      setFiles([]);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = async () => {
    if (!onRetry || !canRetry || retrySubmitting) return;
    setRetrySubmitting(true);
    try {
      await onRetry();
    } finally {
      setRetrySubmitting(false);
    }
  };

  const percent = resolveProgressPercent(kb.progress);
  const showTaskLogs =
    task?.kind === "upload" ||
    task?.kind === "create" ||
    task?.kind === "reindex" ||
    task?.kind === "retry";
  const taskLogTitle =
    task?.kind === "create"
      ? "创建进度"
      : task?.kind === "retry"
        ? "重试进度"
        : task?.kind === "reindex"
          ? "重建索引进度"
          : "上传进度";

  return (
    <Flex vertical gap={20}>
      {isTutorKb ? (
        <Card size="small" title="文档管理（教学域通道）">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            tutor
            域知识库的文档上传/文件树/解析进度由教学域管理（tutor
            知识库页——vendor 通道），本页为注册表镜像不重复入口。
          </Typography.Text>
        </Card>
      ) : (
        <>
          <div>
            <Typography.Text style={{ fontSize: 13, fontWeight: 500 }}>
              添加文档
            </Typography.Text>
            <div style={{ marginTop: 2, fontSize: 11.5, color: MUTED }}>
              拖拽文件到此处加入当前知识库。新文件会按当前激活的 embedding
              模型建立索引。
            </div>
          </div>

          {blockedReason && (
            <div
              style={{
                borderRadius: 8,
                border: "1px solid #fde68a",
                background: "#fffbeb",
                padding: "8px 12px",
                fontSize: 12,
                color: "#b45309",
              }}
            >
              {blockedReason}
            </div>
          )}

          {isError && !blockedReason && (
            <Flex
              wrap="wrap"
              align="center"
              justify="space-between"
              gap={8}
              style={{
                borderRadius: 8,
                border: "1px solid #fde68a",
                background: "#fffbeb",
                padding: "8px 12px",
                fontSize: 12,
                color: "#b45309",
              }}
            >
              <span style={{ minWidth: 0, flex: "1 1 auto" }}>
                The last indexing run failed. Remove the file(s) that failed in
                the Files tab, upload replacements below, or retry to rebuild
                from the current documents.
              </span>
              {onRetry && (
                <Button
                  size="small"
                  onClick={handleRetry}
                  disabled={!canRetry || retrySubmitting}
                  icon={
                    retrySubmitting || isRetryingHere ? (
                      <LoadingOutlined spin />
                    ) : (
                      <SyncOutlined />
                    )
                  }
                  style={{
                    flexShrink: 0,
                    border: "1px solid #fcd34d",
                    background: "#fef3c7",
                    color: "#92400e",
                    fontWeight: 500,
                    fontSize: 11.5,
                  }}
                >
                  {retrySubmitting || isRetryingHere
                    ? "正在重试…"
                    : "重试索引"}
                </Button>
              )}
            </Flex>
          )}

          <FileDropZone
            files={files}
            onChange={setFiles}
            uploadPolicy={uploadPolicy}
            disabled={!canUpload || isUploadingHere}
          />

          <Flex justify="flex-end">
            <Button
              type="primary"
              onClick={handleSubmit}
              disabled={!canSubmit}
              loading={submitting || isUploadingHere}
              icon={<UploadOutlined />}
              style={{ fontSize: 13 }}
            >
              上传
            </Button>
          </Flex>
        </>
      )}

      {showTaskLogs &&
        task &&
        (task.taskId || task.logs.length > 0 || task.executing) && (
          <Flex vertical gap={8}>
            <Flex
              align="center"
              justify="space-between"
              style={{ fontSize: 11, color: MUTED }}
            >
              <span>
                {task.label}
                {task.taskId ? ` · ${task.taskId}` : ""}
              </span>
              {task.executing && percent > 0 && (
                <span style={{ fontWeight: 500, color: "#1f1f1f" }}>
                  {percent}%
                </span>
              )}
            </Flex>
            <ProcessLogs
              logs={task.logs}
              executing={task.executing}
              title={taskLogTitle}
            />
            {task.executing && (
              <Progress
                percent={Math.max(percent, 4)}
                showInfo={false}
                strokeWidth={6}
              />
            )}
            {task.error && (
              <div
                style={{
                  borderRadius: 8,
                  border: "1px solid #fecaca",
                  background: "#fef2f2",
                  padding: "8px 12px",
                  fontSize: 12,
                  color: "#b91c1c",
                }}
              >
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontFamily: MONO,
                    fontSize: 11,
                    lineHeight: 1.6,
                  }}
                >
                  {task.error}
                </pre>
              </div>
            )}
          </Flex>
        )}

      <KbUpdateHistory entries={history} onClear={onClearHistory} />
    </Flex>
  );
}
