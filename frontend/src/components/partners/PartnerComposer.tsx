/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerComposer.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover 用事件直写；group-hover 显隐的附件删除钮用 hover 态承载；
 * ::placeholder 由模块加载时注入一次的 CSS 承载，同批5 settings/shared.tsx 口径）；
 * 拖放计数器/斜杠面板/IME 逻辑逐字一致。@/lib/* → ../../lib/*（其中 composer-keyboard/
 * doc-attachments/attachment-limits/file-attachments/use-auto-sized-textarea/
 * use-ime-composing/partners-api 为本批 1:1 补件）。
 * lucide-react→antd 图标登记：ArrowUp → ArrowUpOutlined；Info → InfoCircleOutlined；
 * Paperclip → PaperClipOutlined；Square（停止实心方块）→ BorderOutlined（antd 无
 * 实心 stop 方块图标，登记近似）；X → CloseOutlined。
 *
 * Compact composer for partner chat. Keeps the partner surface focused while
 * supporting the same file intake paths users expect in the main chat:
 * picker, paste, and drag/drop.
 */

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpOutlined,
  BorderOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  PaperClipOutlined,
} from "@ant-design/icons";
import { shouldSubmitOnEnter } from "../../lib/composer-keyboard";
import {
  getPartnerCommands,
  type PartnerCommandInfo,
} from "../../lib/partners-api";
import {
  ATTACHMENT_ACCEPT,
  classifyFile,
  docIconFor,
  formatBytes,
  isSvgFilename,
} from "../../lib/doc-attachments";
import { useAttachmentLimits } from "../../lib/attachment-limits";
import {
  extractBase64FromDataUrl,
  readFileAsDataUrl,
} from "../../lib/file-attachments";
import { useAutoSizedTextarea } from "../../lib/use-auto-sized-textarea";
import { useImeComposing } from "../../lib/use-ime-composing";

const ZH_MESSAGES: Record<string, string> = {
  "File too large: {{name}}": "文件过大：{{name}}",
  "Too many files, skipped some": "附件总量超出限制，已跳过部分文件",
  "Unsupported file type: {{name}}": "不支持的文件类型：{{name}}",
  "Drop files here": "拖拽文件到此处",
  "Images, Office docs, code & text": "图片、Office 文档、代码和文本",
  "Remove attachment": "移除附件",
  "Attachment preview": "附件预览",
  "Attach files": "上传附件",
  Tips: "用法提示",
  "Type / to see commands — start a new conversation, view history, toggle tools, and more.":
    "输入 / 查看命令——开启新对话、查看历史、切换工具等。",
  "Attach images or documents with the clip, or just drag them in.":
    "点回形针添加图片或文档，或直接拖拽进来。",
  Stop: "停止",
  Send: "发送",
  "Type a message...": "输入消息…",
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

/** ::placeholder 色无法内联——模块加载时注入一次（CRA 无 SSR）。 */
const STYLE_ID = "dsh-partner-composer-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent =
    ".dsh-partner-composer-textarea::placeholder{color:var(--muted-foreground, #64748b)}";
  document.head.appendChild(styleEl);
}

const MONO_FONT =
  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace';

export interface PartnerPendingAttachment {
  type: "image" | "file";
  filename: string;
  base64: string;
  previewUrl?: string;
  size: number;
  mimeType?: string;
}

export const PartnerComposer = memo(function PartnerComposer({
  onSend,
  onStop,
  disabled,
  streaming,
  placeholder,
}: {
  onSend: (content: string, attachments: PartnerPendingAttachment[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  streaming?: boolean;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<PartnerPendingAttachment[]>(
    [],
  );
  const attachmentLimits = useAttachmentLimits();
  const [dragging, setDragging] = useState(false);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [commands, setCommands] = useState<PartnerCommandInfo[]>([]);
  const [slashClosed, setSlashClosed] = useState(false);
  const [slashIndex, setSlashIndex] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const [attachHover, setAttachHover] = useState(false);
  const [helpHover, setHelpHover] = useState(false);
  const [hoveredAttachment, setHoveredAttachment] = useState<number | null>(
    null,
  );
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCounterRef = useRef(0);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { isComposingRef, onCompositionStart, onCompositionEnd } =
    useImeComposing();

  useAutoSizedTextarea(textareaRef, input, { min: 24, max: 180 });

  // Slash commands (same 5 the IM channels expose) — fetched once; the palette
  // is partner-independent so no id is needed.
  useEffect(() => {
    let cancelled = false;
    void getPartnerCommands()
      .then((next) => {
        if (!cancelled) setCommands(next);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // The menu is active while the input is a bare "/word" (no space yet) and the
  // user hasn't dismissed it. Typing reopens it; Escape / accept closes it.
  const slashMatch = /^\/([a-z]*)$/i.exec(input);
  const slashQuery = slashMatch ? slashMatch[1].toLowerCase() : null;
  const slashMatches = useMemo(
    () =>
      slashQuery !== null
        ? commands.filter((c) =>
            c.command.slice(1).toLowerCase().startsWith(slashQuery),
          )
        : [],
    [commands, slashQuery],
  );
  const slashOpen = !slashClosed && slashMatches.length > 0;
  const boundedSlashIndex = Math.min(slashIndex, slashMatches.length - 1);

  const acceptCommand = useCallback((command: PartnerCommandInfo) => {
    // Arg-taking commands keep the menu out of the way with a trailing space;
    // zero-arg ones are left ready to send.
    setInput(command.arg_hint ? `${command.command} ` : command.command);
    setSlashClosed(true);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const showAttachmentError = useCallback((message: string) => {
    setAttachmentError(message);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    errorTimerRef.current = setTimeout(() => {
      setAttachmentError(null);
      errorTimerRef.current = null;
    }, 4000);
  }, []);

  const filterFiles = useCallback(
    (files: File[]) => {
      let runningTotal = attachments.reduce((sum, item) => sum + item.size, 0);
      const accepted: File[] = [];
      const rejected: {
        name: string;
        reason: "unsupported" | "too_large" | "quota";
      }[] = [];

      for (const file of files) {
        if (!classifyFile(file)) {
          rejected.push({ name: file.name, reason: "unsupported" });
          continue;
        }
        if (file.size > attachmentLimits.maxFileBytes) {
          rejected.push({ name: file.name, reason: "too_large" });
          continue;
        }
        if (runningTotal + file.size > attachmentLimits.maxTotalBytes) {
          rejected.push({ name: file.name, reason: "quota" });
          break;
        }
        runningTotal += file.size;
        accepted.push(file);
      }

      if (rejected.length) {
        const first = rejected[0];
        if (first.reason === "too_large") {
          showAttachmentError(
            t("File too large: {{name}}", { name: first.name }),
          );
        } else if (first.reason === "quota") {
          showAttachmentError(t("Too many files, skipped some"));
        } else {
          showAttachmentError(
            t("Unsupported file type: {{name}}", { name: first.name }),
          );
        }
      }

      return accepted;
    },
    [attachments, attachmentLimits, showAttachmentError, t],
  );

  const fileToAttachment = useCallback(
    async (file: File): Promise<PartnerPendingAttachment> => {
      const raw = await readFileAsDataUrl(file);
      const svg = isSvgFilename(file.name) || file.type === "image/svg+xml";
      const isImage = !svg && file.type.startsWith("image/");
      return {
        type: isImage ? "image" : "file",
        filename: file.name,
        base64: extractBase64FromDataUrl(raw),
        previewUrl: isImage || svg ? raw : undefined,
        size: file.size,
        mimeType: file.type || undefined,
      };
    },
    [],
  );

  const addFiles = useCallback(
    async (files: File[]) => {
      if (disabled) return;
      const accepted = filterFiles(files);
      if (!accepted.length) return;
      const next = await Promise.all(accepted.map(fileToAttachment));
      setAttachments((prev) => [...prev, ...next]);
    },
    [disabled, fileToAttachment, filterFiles],
  );

  const submit = useCallback(() => {
    const content = input.trim();
    if ((!content && attachments.length === 0) || disabled) return;
    onSend(content, attachments);
    setInput("");
    setAttachments([]);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [attachments, disabled, input, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // When the slash menu is open it owns the arrow/enter/tab/escape keys.
      if (slashOpen && !isComposingRef.current) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSlashIndex((i) => Math.min(i + 1, slashMatches.length - 1));
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setSlashIndex((i) => Math.max(i - 1, 0));
          return;
        }
        if (e.key === "Enter" || e.key === "Tab") {
          e.preventDefault();
          acceptCommand(slashMatches[boundedSlashIndex]);
          return;
        }
        if (e.key === "Escape") {
          e.preventDefault();
          setSlashClosed(true);
          return;
        }
      }
      if (shouldSubmitOnEnter(e, isComposingRef.current)) {
        e.preventDefault();
        submit();
      }
    },
    [
      acceptCommand,
      boundedSlashIndex,
      slashMatches,
      slashOpen,
      submit,
      isComposingRef,
    ],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      setSlashClosed(false); // typing always re-arms the menu
      setSlashIndex(0);
    },
    [],
  );

  const handlePaste = useCallback(
    async (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const files = Array.from(event.clipboardData.items)
        .filter((item) => item.kind === "file")
        .map((item) => item.getAsFile())
        .filter((file): file is File => file !== null);
      if (!files.length) return;
      event.preventDefault();
      await addFiles(files);
    },
    [addFiles],
  );

  const handleDragEnter = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      dragCounterRef.current += 1;
      if (event.dataTransfer.types.includes("Files")) setDragging(true);
    },
    [],
  );

  const handleDragLeave = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      dragCounterRef.current -= 1;
      if (dragCounterRef.current <= 0) {
        dragCounterRef.current = 0;
        setDragging(false);
      }
    },
    [],
  );

  const handleDragOver = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
    },
    [],
  );

  const handleDrop = useCallback(
    async (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      dragCounterRef.current = 0;
      setDragging(false);
      await addFiles(Array.from(event.dataTransfer.files));
    },
    [addFiles],
  );

  const handleFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const picked = Array.from(event.target.files ?? []);
      if (picked.length) void addFiles(picked);
      event.target.value = "";
    },
    [addFiles],
  );

  const removeAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const canSend =
    (!!input.trim() || attachments.length > 0) && !disabled && !streaming;

  return (
    <div
      style={{
        position: "relative",
        borderRadius: 16,
        border: `1px solid ${
          dragging ? "var(--primary, #2563eb)" : "var(--border, #e2e8f0)"
        }`,
        background: dragging
          ? "rgba(37, 99, 235, 0.03)"
          : "var(--card, #ffffff)",
        boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        transition: "border-color 150ms, background-color 150ms",
      }}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {dragging && (
        <div
          style={{
            pointerEvents: "none",
            position: "absolute",
            inset: 0,
            zIndex: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 16,
            border: "2px dashed rgba(37, 99, 235, 0.5)",
            background: "rgba(37, 99, 235, 0.04)",
            backdropFilter: "blur(1px)",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
              color: "var(--primary, #2563eb)",
            }}
          >
            <PaperClipOutlined style={{ fontSize: 20 }} />
            <span style={{ fontSize: 13, fontWeight: 500 }}>
              {t("Drop files here")}
            </span>
            <span
              style={{
                fontSize: 11,
                color: "rgba(37, 99, 235, 0.7)",
              }}
            >
              {t("Images, Office docs, code & text")}
            </span>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ATTACHMENT_ACCEPT}
        onChange={handleFileInputChange}
        style={{ display: "none" }}
        aria-hidden="true"
        tabIndex={-1}
      />

      {slashOpen && (
        <div
          style={{
            position: "absolute",
            bottom: "100%",
            left: 0,
            zIndex: 20,
            marginBottom: 8,
            width: "100%",
            maxWidth: 384,
            overflow: "hidden",
            borderRadius: 12,
            border: "1px solid var(--border, #e2e8f0)",
            background: "var(--card, #ffffff)",
            boxShadow:
              "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
          }}
        >
          {slashMatches.map((command, index) => (
            <button
              key={command.command}
              type="button"
              // onMouseDown (not onClick) so the textarea doesn't blur first.
              onMouseDown={(e) => {
                e.preventDefault();
                acceptCommand(command);
              }}
              onMouseEnter={() => setSlashIndex(index)}
              style={{
                display: "flex",
                width: "100%",
                alignItems: "baseline",
                gap: 8,
                padding: "8px 12px",
                textAlign: "left",
                border: "none",
                cursor: "pointer",
                background:
                  index === boundedSlashIndex
                    ? "var(--muted, #f1f5f9)"
                    : "transparent",
                transition: "background-color 150ms",
              }}
            >
              <span
                style={{
                  fontFamily: MONO_FONT,
                  fontSize: 12.5,
                  color: "var(--foreground, #0f172a)",
                }}
              >
                {command.command}
              </span>
              {command.arg_hint && (
                <span
                  style={{
                    fontFamily: MONO_FONT,
                    fontSize: 11,
                    color: "var(--muted-foreground, #64748b)",
                  }}
                >
                  {command.arg_hint}
                </span>
              )}
              <span
                style={{
                  marginLeft: "auto",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  paddingLeft: 12,
                  fontSize: 11.5,
                  color: "var(--muted-foreground, #64748b)",
                }}
              >
                {command.description}
              </span>
            </button>
          ))}
        </div>
      )}

      <textarea
        ref={textareaRef}
        value={input}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onCompositionStart={onCompositionStart}
        onCompositionEnd={onCompositionEnd}
        placeholder={placeholder ?? t("Type a message...")}
        rows={1}
        maxLength={32000}
        disabled={disabled || streaming}
        className="dsh-partner-composer-textarea"
        style={{
          display: "block",
          width: "100%",
          resize: "none",
          background: "transparent",
          padding: "12px 14px 4px",
          fontSize: 14,
          lineHeight: 1.625,
          color: "var(--foreground, #0f172a)",
          outline: "none",
          border: "none",
          opacity: disabled || streaming ? 0.5 : 1,
        }}
      />

      {!!attachments.length && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            padding: "0 14px 8px",
          }}
        >
          {attachments.map((attachment, index) => {
            const removeLabel = t("Remove attachment");
            const hovered = hoveredAttachment === index;
            const removeButton = (
              <button
                type="button"
                onClick={() => removeAttachment(index)}
                onMouseEnter={() => setHoveredAttachment(index)}
                onMouseLeave={() => setHoveredAttachment(null)}
                aria-label={removeLabel}
                style={{
                  position: "absolute",
                  right: -6,
                  top: -6,
                  display: "flex",
                  height: 16,
                  width: 16,
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 9999,
                  border: "none",
                  padding: 0,
                  background: "var(--foreground, #0f172a)",
                  color: "var(--background, #f6f8fc)",
                  boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                  cursor: "pointer",
                  opacity: hovered ? 1 : 0,
                  transition: "opacity 150ms",
                }}
              >
                <CloseOutlined style={{ fontSize: 10 }} />
              </button>
            );
            if (
              (attachment.type === "image" ||
                isSvgFilename(attachment.filename)) &&
              attachment.previewUrl
            ) {
              return (
                <div
                  key={`${attachment.filename}-${index}`}
                  onMouseEnter={() => setHoveredAttachment(index)}
                  onMouseLeave={() => setHoveredAttachment(null)}
                  style={{ position: "relative" }}
                >
                  <div
                    style={{
                      height: 56,
                      width: 56,
                      overflow: "hidden",
                      borderRadius: 8,
                      border: "1px solid var(--border, #e2e8f0)",
                      background: "rgba(241, 245, 249, 0.35)",
                    }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={attachment.previewUrl}
                      alt={attachment.filename || t("Attachment preview")}
                      style={{
                        height: "100%",
                        width: "100%",
                        objectFit: isSvgFilename(attachment.filename)
                          ? "contain"
                          : "cover",
                        padding: isSvgFilename(attachment.filename) ? 4 : 0,
                      }}
                    />
                  </div>
                  {removeButton}
                </div>
              );
            }

            const spec = docIconFor(attachment.filename);
            const Icon = spec.Icon;
            return (
              <div
                key={`${attachment.filename}-${index}`}
                onMouseEnter={() => setHoveredAttachment(index)}
                onMouseLeave={() => setHoveredAttachment(null)}
                style={{ position: "relative" }}
              >
                <div
                  style={{
                    display: "flex",
                    height: 56,
                    width: 150,
                    alignItems: "center",
                    gap: 8,
                    borderRadius: 8,
                    border: "1px solid var(--border, #e2e8f0)",
                    background: "var(--card, #ffffff)",
                    padding: "0 8px",
                    textAlign: "left",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      height: 36,
                      width: 36,
                      flexShrink: 0,
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: 6,
                      background: "rgba(241, 245, 249, 0.6)",
                    }}
                  >
                    <Icon
                      style={{ fontSize: 19, color: spec.tint }}
                    />
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontSize: 12,
                        fontWeight: 500,
                        color: "var(--foreground, #0f172a)",
                      }}
                    >
                      {attachment.filename}
                    </div>
                    <div
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontSize: 10,
                        textTransform: "uppercase",
                        color: "var(--muted-foreground, #64748b)",
                      }}
                    >
                      {spec.label} · {formatBytes(attachment.size)}
                    </div>
                  </div>
                </div>
                {removeButton}
              </div>
            );
          })}
        </div>
      )}

      {attachmentError && (
        <div
          style={{
            padding: "0 14px 8px",
            fontSize: 11,
            color: "#dc2626",
          }}
        >
          {attachmentError}
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 8px 8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || streaming}
            onMouseEnter={() => setAttachHover(true)}
            onMouseLeave={() => setAttachHover(false)}
            aria-label={t("Attach files")}
            title={t("Attach files")}
            style={{
              display: "flex",
              height: 28,
              width: 28,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 9999,
              border: "none",
              padding: 0,
              background: attachHover
                ? "var(--muted, #f1f5f9)"
                : "transparent",
              color: attachHover
                ? "var(--foreground, #0f172a)"
                : "var(--muted-foreground, #64748b)",
              cursor: disabled || streaming ? "default" : "pointer",
              opacity: disabled || streaming ? 0.3 : 1,
              transition: "background-color 150ms, color 150ms",
            }}
          >
            <PaperClipOutlined style={{ fontSize: 16 }} />
          </button>
          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
            }}
            onMouseEnter={() => setShowHelp(true)}
            onMouseLeave={() => setShowHelp(false)}
          >
            <button
              type="button"
              aria-label={t("Tips")}
              style={{
                display: "flex",
                height: 28,
                width: 28,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 9999,
                border: "none",
                padding: 0,
                background: helpHover
                  ? "var(--muted, #f1f5f9)"
                  : "transparent",
                color: helpHover
                  ? "var(--foreground, #0f172a)"
                  : "var(--muted-foreground, #64748b)",
                cursor: "pointer",
                transition: "background-color 150ms, color 150ms",
              }}
            >
              <InfoCircleOutlined style={{ fontSize: 16 }} />
            </button>
            {showHelp && (
              <div
                style={{
                  position: "absolute",
                  bottom: "100%",
                  left: 0,
                  zIndex: 20,
                  marginBottom: 8,
                  width: 256,
                  borderRadius: 12,
                  border: "1px solid var(--border, #e2e8f0)",
                  background: "var(--card, #ffffff)",
                  padding: 12,
                  fontSize: 11.5,
                  lineHeight: 1.625,
                  color: "var(--muted-foreground, #64748b)",
                  boxShadow:
                    "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
                }}
              >
                <p
                  style={{
                    marginBottom: 4,
                    fontWeight: 500,
                    color: "var(--foreground, #0f172a)",
                    margin: "0 0 4px",
                  }}
                >
                  {t("Tips")}
                </p>
                <p style={{ margin: 0 }}>
                  {t(
                    "Type / to see commands — start a new conversation, view history, toggle tools, and more.",
                  )}
                </p>
                <p style={{ marginTop: 6 }}>
                  {t(
                    "Attach images or documents with the clip, or just drag them in.",
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
        {streaming ? (
          <button
            type="button"
            onClick={onStop}
            aria-label={t("Stop")}
            title={t("Stop")}
            style={{
              display: "flex",
              height: 28,
              width: 28,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 9999,
              border: "none",
              padding: 0,
              background: "var(--foreground, #0f172a)",
              color: "var(--background, #f6f8fc)",
              cursor: "pointer",
            }}
          >
            <BorderOutlined
              style={{ fontSize: 12, color: "currentColor" }}
            />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            aria-label={t("Send")}
            style={{
              display: "flex",
              height: 28,
              width: 28,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 9999,
              border: "none",
              padding: 0,
              background: "var(--primary, #2563eb)",
              color: "var(--primary-foreground, #ffffff)",
              cursor: "pointer",
              opacity: canSend ? 1 : 0.3,
            }}
          >
            <ArrowUpOutlined style={{ fontSize: 16 }} />
          </button>
        )}
      </div>
    </div>
  );
});
