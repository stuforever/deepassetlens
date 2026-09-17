/**
 * 复刻自 DeepTutor 原仓 web/components/knowledge/FileDropZone.tsx（377 行，整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. 源 @/lib/knowledge-helpers 的纯校验工具（formatFileSize / getFileExtension /
 *    selectionFileId / mergeSelectedFiles / validateFiles + ValidatedSelectionFile /
 *    ValidatedFileSelection 类型）→ 按名 import './knowledge-helpers'（并行批件，逐函数移植）；
 *    validateFiles 的 t 契约 → 本文件 zhT()（键=英文原文，映射对拍 zh/app.json：
 *    不支持的文件类型 / 该文件超过了 {size} 的大小限制。/ 无扩展名），与 KbDocumentsSection 同款；
 * 3. 主拖放区 → Upload.Dragger：beforeUpload 恒返回 false 手动控制上传；fileList 受控常空
 *    （onChange 只反映当批选择，不累积），文件统一取 originFileObj 原始 File——antd 在
 *    beforeUpload=false 时会克隆 File（丢 webkitRelativePath / lastModified），目录结构属性
 *    随原始 File 对象旁路透传，数据层 appendFilesWithPaths 直读 file.webkitRelativePath；
 *    组件只把 File[] 原样上抛 onChange（mergeSelectedFiles 按 name:size:lastModified 去重合并）；
 * 4. 拖拽态状态机（enter 深度计数 / over 持续预览 / leave 递减 / drop 复位；有效=sky、
 *    含无效=amber）逐字移植，挂 Dragger 外层 div（antd 不转发 onDragEnter，rc-upload 也不
 *    stopPropagation，事件可冒泡到外层）；文件本体 intake 走 rc-upload drop 通道（同取
 *    dataTransfer.files，外层 onDrop 仅复位拖拽态，不重复合并）；
 * 5. 说明：accept 不传给 Dragger——rc-upload 会在 drop 路径按 accept 过滤文件，会吃掉
 *    「拖入不受支持文件」的 amber 态与逐文件校验行；源仓 drop 全量入列、仅由 validateFiles
 *    标记不拦截。点击选择器因此不做系统级预过滤，超策略文件仍会被标记为「需要处理」；
 * 6. 「或选择整个文件夹」→ 独立 Upload directory（=webkitdirectory+directory），!disabled
 *    才渲染，目录 input 本就不带 accept（与源一致）；
 * 7. lucide → @ant-design/icons：Files→InboxOutlined、AlertTriangle→WarningOutlined、
 *    CheckCircle2→CheckCircleOutlined、FileText→FileTextOutlined、X→CloseOutlined；
 * 8. Tailwind → antd theme.useToken() + 内联样式（amber/sky/emerald 调色板 hex 直用）；
 *    t() 文案按基线 §5 内联中文。UploadChangeParam/UploadFile 类型取自 antd/es/upload
 *    （antd 5.12 根入口未 re-export UploadChangeParam）。
 */
import { useCallback, useMemo, useRef, useState, type DragEvent } from "react";
import {
  CheckCircleOutlined,
  CloseOutlined,
  FileTextOutlined,
  InboxOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Button, Upload, theme } from "antd";
import type { RcFile, UploadChangeParam, UploadFile } from "antd/es/upload";
import type { KnowledgeUploadPolicy } from "./knowledge-api";
import {
  formatFileSize,
  mergeSelectedFiles,
  selectionFileId,
  validateFiles,
  type ValidatedFileSelection,
} from "./knowledge-helpers";

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

/* ---------- 组件本体 ---------- */

interface DropState {
  active: boolean;
  invalid: boolean;
  draggedCount: number;
}

const EMPTY_DROP_STATE: DropState = {
  active: false,
  invalid: false,
  draggedCount: 0,
};

interface FileDropZoneProps {
  files: File[];
  onChange: (files: File[]) => void;
  uploadPolicy: KnowledgeUploadPolicy;
  disabled?: boolean;
  compact?: boolean;
  hidePolicyHint?: boolean;
}

export default function FileDropZone({
  files,
  onChange,
  uploadPolicy,
  disabled = false,
  compact = false,
  hidePolicyHint = false,
}: FileDropZoneProps) {
  const { token } = theme.useToken();
  const depthRef = useRef(0);
  const [dropState, setDropState] = useState<DropState>(EMPTY_DROP_STATE);

  const selection = useMemo<ValidatedFileSelection>(
    () => validateFiles(files, uploadPolicy, zhT),
    [files, uploadPolicy],
  );

  const previewDropped = useCallback(
    (incoming: File[]) => {
      const validated = validateFiles(incoming, uploadPolicy, zhT);
      return {
        count: incoming.length,
        invalid: validated.invalidFiles.length > 0,
      };
    },
    [uploadPolicy],
  );

  const reset = useCallback(() => {
    depthRef.current = 0;
    setDropState(EMPTY_DROP_STATE);
  }, []);

  const dragHasFiles = (event: DragEvent<HTMLElement>) =>
    Array.from(event.dataTransfer.types).includes("Files");

  const handleEnter = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (disabled) return;
      if (!dragHasFiles(event)) return;
      event.preventDefault();
      event.stopPropagation();
      depthRef.current += 1;
      const incoming = Array.from(event.dataTransfer.items)
        .filter((item) => item.kind === "file")
        .map((item) => item.getAsFile())
        .filter((file): file is File => Boolean(file));
      const preview = previewDropped(incoming);
      setDropState({
        active: true,
        invalid: preview.invalid,
        draggedCount: preview.count,
      });
    },
    [disabled, previewDropped],
  );

  const handleOver = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (disabled) return;
      if (!dragHasFiles(event)) return;
      event.preventDefault();
      event.stopPropagation();
      event.dataTransfer.dropEffect = "copy";
      const incoming = Array.from(event.dataTransfer.items)
        .filter((item) => item.kind === "file")
        .map((item) => item.getAsFile())
        .filter((file): file is File => Boolean(file));
      const preview = previewDropped(incoming);
      setDropState({
        active: true,
        invalid: preview.invalid,
        draggedCount: preview.count,
      });
    },
    [disabled, previewDropped],
  );

  const handleLeave = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (disabled) return;
      if (!dragHasFiles(event)) return;
      event.preventDefault();
      event.stopPropagation();
      depthRef.current = Math.max(0, depthRef.current - 1);
      if (depthRef.current === 0) reset();
    },
    [disabled, reset],
  );

  // 文件本体由 Upload.Dragger 的 rc-upload drop 通道接管（同取 dataTransfer.files，
  // 不按 accept 过滤），这里仅复位拖拽态；onChange 合并在 handleUploadChange 完成。
  const handleDrop = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (disabled) return;
      if (!dragHasFiles(event)) return;
      event.preventDefault();
      event.stopPropagation();
      reset();
    },
    [disabled, reset],
  );

  const handleUploadChange = useCallback(
    (info: UploadChangeParam<UploadFile>) => {
      // beforeUpload=false 时 antd 会克隆 File（丢 webkitRelativePath/lastModified），
      // 统一取 originFileObj 原始 File：目录结构属性原样保留（数据层 appendFilesWithPaths
      // 直读 file.webkitRelativePath），去重 id 也与源一致（name:size:lastModified）。
      const picked = info.fileList
        .map((item) => item.originFileObj)
        .filter((file): file is RcFile => Boolean(file));
      if (picked.length) onChange(mergeSelectedFiles(files, picked));
    },
    [files, onChange],
  );

  const padding = compact ? "20px 16px" : "28px 20px";
  const dragActive = dropState.active;
  const dragBorderColor = dragActive
    ? dropState.invalid
      ? "#fbbf24" // amber-400
      : "#38bdf8" // sky-400
    : token.colorBorder;
  const dragBackground = dragActive
    ? dropState.invalid
      ? "rgba(254, 243, 199, 0.6)" // amber-50/60
      : "rgba(240, 249, 255, 0.6)" // sky-50/60
    : token.colorBgContainer;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* 拖拽态状态机挂外层 div（antd 不转发 onDragEnter；rc-upload 不 stopPropagation，
          事件可冒泡至此，源 handleEnter/Over/Leave/Drop 逻辑逐字保留）。 */}
      <div
        onDragEnter={handleEnter}
        onDragOver={handleOver}
        onDragLeave={handleLeave}
        onDrop={handleDrop}
      >
        <Upload.Dragger
          multiple
          disabled={disabled}
          showUploadList={false}
          fileList={[]}
          beforeUpload={() => false}
          onChange={handleUploadChange}
          style={{
            padding,
            borderColor: dragBorderColor,
            background: dragBackground,
            cursor: disabled ? "not-allowed" : "pointer",
            opacity: disabled ? 0.5 : 1,
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              textAlign: "center",
            }}
          >
            <InboxOutlined
              style={{ fontSize: 20, color: token.colorTextSecondary }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: token.colorText,
                }}
              >
                {dragActive
                  ? dropState.invalid
                    ? "拖拽的文件里有不受支持的类型"
                    : "松开即可添加这些文件"
                  : files.length
                    ? selection.invalidFiles.length > 0
                      ? `${selection.invalidFiles.length} 个文件不受支持`
                      : `${selection.validFiles.length} 个文件已就绪`
                    : "选择文件..."}
              </div>
              <p
                style={{
                  margin: 0,
                  fontSize: 11,
                  color: token.colorTextSecondary,
                }}
              >
                {dragActive
                  ? dropState.draggedCount > 0
                    ? `检测到 ${dropState.draggedCount} 个文件`
                    : "松开以上传这些文件"
                  : files.length
                    ? formatFileSize(selection.totalBytes)
                    : "点击选择受支持的文档"}
              </p>
            </div>
          </div>
        </Upload.Dragger>
      </div>

      {!disabled && (
        <Upload
          directory
          multiple
          showUploadList={false}
          fileList={[]}
          beforeUpload={() => false}
          onChange={handleUploadChange}
        >
          <Button
            type="text"
            size="small"
            style={{
              fontSize: 11,
              fontWeight: 500,
              height: 18,
              padding: "0 2px",
              color: token.colorTextSecondary,
            }}
          >
            或选择整个文件夹
          </Button>
        </Upload>
      )}

      {!hidePolicyHint && (
        <p
          style={{
            margin: 0,
            fontSize: 11,
            color: token.colorTextSecondary,
          }}
        >
          {`${uploadPolicy.extensions.length} 种类型 · 单个文件最大：${formatFileSize(uploadPolicy.max_file_size_bytes)}`}
        </p>
      )}

      {selection.items.length > 0 && (
        <SelectionSummary
          selection={selection}
          onRemove={(id) =>
            onChange(files.filter((file) => selectionFileId(file) !== id))
          }
          onClear={() => onChange([])}
        />
      )}
    </div>
  );
}

function SelectionSummary({
  selection,
  onRemove,
  onClear,
}: {
  selection: ValidatedFileSelection;
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  const { token } = theme.useToken();
  const invalidCount = selection.invalidFiles.length;
  const readyCount = selection.validFiles.length;
  const hasIssues = invalidCount > 0;

  return (
    <div
      style={{
        borderRadius: 16,
        border: `1px solid ${hasIssues ? "#fde68a" : "#a7f3d0"}`,
        background: hasIssues
          ? "rgba(254, 243, 199, 0.8)"
          : "rgba(209, 250, 229, 0.7)",
        padding: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 13,
              fontWeight: 500,
              color: token.colorText,
            }}
          >
            {hasIssues ? (
              <WarningOutlined style={{ fontSize: 16, color: "#d97706" }} />
            ) : (
              <CheckCircleOutlined
                style={{ fontSize: 16, color: "#059669" }}
              />
            )}
            {hasIssues
              ? `${readyCount} 个就绪，${invalidCount} 个将跳过`
              : `${readyCount} 个文件已就绪`}
          </div>
          <p
            style={{
              margin: "4px 0 0",
              fontSize: 11,
              color: token.colorTextSecondary,
            }}
          >
            {`${hasIssues ? "不支持的文件将被跳过，其余照常索引。" : "可开始上传"} · ${formatFileSize(selection.totalBytes)}`}
          </p>
        </div>
        <Button size="small" onClick={onClear}>
          清空选择
        </Button>
      </div>

      <div
        style={{
          marginTop: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {selection.items.map((item) => (
          <div
            key={item.id}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              borderRadius: 12,
              border: `1px solid ${item.valid ? "rgba(255, 255, 255, 0.6)" : "#fde68a"}`,
              background: item.valid
                ? "rgba(255, 255, 255, 0.7)"
                : "rgba(254, 243, 199, 0.6)",
              padding: "10px 12px",
            }}
          >
            <div
              style={{
                marginTop: 2,
                borderRadius: 8,
                padding: 8,
                background: item.valid ? "#d1fae5" : "#fef3c7",
                color: item.valid ? "#047857" : "#b45309",
              }}
            >
              <FileTextOutlined style={{ fontSize: 14 }} />
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontSize: 12,
                  fontWeight: 500,
                  color: token.colorText,
                }}
              >
                {item.file.name}
              </div>
              <div
                style={{
                  marginTop: 4,
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.12em",
                  color: token.colorTextSecondary,
                }}
              >
                <span>{item.extension}</span>
                <span>{item.sizeLabel}</span>
                <span
                  style={{
                    borderRadius: 999,
                    padding: "2px 8px",
                    textTransform: "none",
                    letterSpacing: "normal",
                    background: item.valid ? "#d1fae5" : "#fef3c7",
                    color: item.valid ? "#047857" : "#b45309",
                  }}
                >
                  {item.valid ? "已支持" : "需要处理"}
                </span>
              </div>
              {item.error && (
                <p
                  style={{
                    margin: "6px 0 0",
                    fontSize: 11,
                    lineHeight: 1.6,
                    color: "#b45309",
                  }}
                >
                  {item.error}
                </p>
              )}
            </div>
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              title="移除"
              onClick={() => onRemove(item.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
