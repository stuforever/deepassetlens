/**
 * 等价替换 stub：DeepTutor 原仓 web/context/UnifiedChatContext.tsx（2034 行）
 * 在本仓不存在。仅把本批复刻文件以 `import type` 引用的类型原样复制导出
 * （BookChatPanel 引用 MessageAttachment）；类型定义逐字未改。
 */

export interface MessageAttachment {
  type: string;
  filename?: string;
  base64?: string;
  url?: string;
  mime_type?: string;
  /** Stable per-attachment id; matches the URL segment served by /api/attachments. */
  id?: string;
  /** Plain-text rendering of office docs, populated by the backend extractor.
   *  Used by the preview drawer to show "what the LLM saw" for binary docs. */
  extracted_text?: string;
  /** Set on files the assistant produced this turn (exec/code_execution
   *  artifacts) rather than files the user uploaded. Rendered as openable
   *  cards under the assistant message. */
  generated?: boolean;
  /** Byte size of the generated file, for the card's subtitle. */
  size_bytes?: number;
}
