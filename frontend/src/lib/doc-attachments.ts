// IA批6 6.3 lib 补件：1:1 移植自 DeepTutor web/lib/doc-attachments.ts（附件分类/
// 限额常量/图标 spec）。替换点：lucide-react 图标与 LucideIcon 类型 → @ant-design/icons
// （登记：FileType2→FilePdfOutlined；FileText→FileTextOutlined；FileSpreadsheet→
// FileExcelOutlined；Presentation→FilePptOutlined；FileImage→FileImageOutlined；
// FileCode2→CodeOutlined；SquareTerminal→MacCommandOutlined（antd 无终端图标）；
// FileJson→ApiOutlined；Settings2→SettingOutlined；Palette→BgColorsOutlined；
// Braces→CodeOutlined（与 FileCode2 同形、tint 色差区分）；FilePlus2→FileAddOutlined）；
// DocIconSpec.tint 从 tailwind 色类改为等价 CSS 颜色值（text-red-500/80 →
// rgba(239,68,68,0.8) 等），消费方以 style={{ color: spec.tint }} 承载。
// 其余常量/函数逐字一致。
//
// Helpers for drag-and-drop document attachments in the chat composer.
//
// The accepted extension / MIME sets MUST stay in sync with the backend
// `deeptutor/utils/document_extractor.py` (which in turn mirrors the KB
// pipeline's `FileTypeRouter.TEXT_EXTENSIONS`). If you add a new format
// server-side, add it here too.

import type { ComponentType, CSSProperties } from "react";
import {
  ApiOutlined,
  BgColorsOutlined,
  CodeOutlined,
  FileAddOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FilePptOutlined,
  FileTextOutlined,
  MacCommandOutlined,
  SettingOutlined,
} from "@ant-design/icons";

/** antd 图标组件的最小类型面（本 lib 只传引用，不渲染）。 */
export type AntdIconComponent = ComponentType<{ style?: CSSProperties }>;

/** Binary Office formats — handled by dedicated parsers server-side. */
export const OFFICE_EXTS = [".pdf", ".docx", ".xlsx", ".pptx"] as const;

/**
 * Text-like formats — decoded server-side with multi-encoding fallback.
 * Mirrors `FileTypeRouter.TEXT_EXTENSIONS` in the Python codebase. Adding
 * a new extension here without also adding it to the backend will cause
 * the upload to be silently dropped.
 */
export const TEXT_LIKE_EXTS = [
  // Plain text & markup
  ".txt",
  ".text",
  ".log",
  ".md",
  ".markdown",
  ".rst",
  ".asciidoc",
  ".html",
  ".htm",
  ".xml",
  ".svg", // vector image, treated as XML source; rendered via <img> client-side
  // Data & config
  ".json",
  ".jsonc",
  ".json5",
  ".yaml",
  ".yml",
  ".toml",
  ".csv",
  ".tsv",
  ".ini",
  ".cfg",
  ".conf",
  ".env",
  ".properties",
  // Typesetting
  ".tex",
  ".latex",
  ".bib",
  // Stylesheets
  ".css",
  ".scss",
  ".sass",
  ".less",
  // JavaScript / TypeScript family
  ".js",
  ".mjs",
  ".cjs",
  ".ts",
  ".mts",
  ".cts",
  ".jsx",
  ".tsx",
  // Web frameworks
  ".vue",
  ".svelte",
  // Python
  ".py",
  // JVM languages
  ".java",
  ".kt",
  ".kts",
  ".scala",
  ".groovy",
  ".gradle",
  // Systems
  ".c",
  ".h",
  ".cpp",
  ".cc",
  ".cxx",
  ".hpp",
  ".hh",
  ".hxx",
  ".cs",
  ".go",
  ".rs",
  ".zig",
  ".nim",
  // Apple platforms
  ".swift",
  ".m",
  ".mm",
  // Scripting
  ".rb",
  ".php",
  ".pl",
  ".pm",
  ".lua",
  ".r",
  ".jl",
  ".dart",
  // Functional
  ".hs",
  ".clj",
  ".cljs",
  ".cljc",
  ".ex",
  ".exs",
  ".erl",
  ".ml",
  ".mli",
  ".fs",
  ".fsx",
  ".lisp",
  ".lsp",
  ".scm",
  ".rkt",
  // Smart contracts
  ".sol",
  // Shells / editors
  ".sh",
  ".bash",
  ".zsh",
  ".fish",
  ".ps1",
  ".vim",
  // Query / IDL
  ".sql",
  ".graphql",
  ".gql",
  ".proto",
  // Build / infra
  ".cmake",
  ".mk",
  ".tf",
  ".hcl",
  ".nginxconf",
  ".dockerfile",
] as const;

export const SUPPORTED_DOC_EXTS = [...OFFICE_EXTS, ...TEXT_LIKE_EXTS] as const;

export const SUPPORTED_DOC_MIMES = new Set<string>([
  // Office
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  // Common text MIMEs — browsers are inconsistent so the extension fallback
  // in classifyFile is the real workhorse.
  "text/plain",
  "text/markdown",
  "text/html",
  "text/xml",
  "application/xml",
  "application/json",
  "text/csv",
  "text/tab-separated-values",
  "text/yaml",
  "application/yaml",
  "application/x-yaml",
  "text/x-python",
  "application/x-python-code",
  "text/javascript",
  "application/javascript",
  "application/typescript",
  "text/css",
  "text/x-c",
  "text/x-c++",
  "text/x-java",
  "text/x-go",
  "text/x-rust",
  "text/x-ruby",
  "text/x-php",
  "text/x-shellscript",
  "application/sql",
  "application/toml",
]);

/**
 * Built-in attachment caps. These are compile-time fallbacks only — the
 * effective limits come from the backend policy (see
 * `lib/attachment-limits.ts` / the /settings/attachments page) and must match
 * the backend defaults in `deeptutor/services/config/runtime_settings.py`.
 */
export const DEFAULT_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024;
export const DEFAULT_MAX_TOTAL_ATTACHMENT_BYTES = 25 * 1024 * 1024;

/**
 * `accept` attribute for the chat composer's file picker. Mirrors the formats
 * the drag-and-drop / paste paths accept (see `classifyFile`). Listing both
 * MIME types and extensions improves cross-OS reliability — Windows in
 * particular often reports an empty `File.type` for OOXML files.
 */
export const ATTACHMENT_ACCEPT = [
  "image/*",
  ...SUPPORTED_DOC_EXTS,
  ...Array.from(SUPPORTED_DOC_MIMES),
].join(",");

export type FileKind = "image" | "doc";

export function extOf(filename: string): string {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx).toLowerCase() : "";
}

/**
 * Classify a dropped/pasted file. Returns null for unsupported types.
 *
 * SVG is classified as "doc" even though its MIME starts with `image/`, because
 * vision models reject SVG and sending the XML source lets the LLM reason about
 * the vector content. The composer still renders a thumbnail via a raw <img>
 * tag (safe — scripts inside an SVG don't run under <img> context).
 *
 * Otherwise MIME wins; extension is a fallback because browsers frequently
 * report empty `File.type` for OOXML, code, and config files.
 */
export function classifyFile(file: File): FileKind | null {
  const ext = extOf(file.name);
  if (ext === ".svg" || file.type === "image/svg+xml") return "doc";
  if (file.type && file.type.startsWith("image/")) return "image";
  if (file.type && SUPPORTED_DOC_MIMES.has(file.type)) return "doc";
  if (ext && (SUPPORTED_DOC_EXTS as readonly string[]).includes(ext))
    return "doc";
  return null;
}

/** Whether a filename refers to an SVG (case-insensitive). */
export function isSvgFilename(filename: string): boolean {
  return extOf(filename) === ".svg";
}

/**
 * Human-readable byte size: `1.2 MB`, `34.0 KB`.
 */
export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export interface DocIconSpec {
  Icon: AntdIconComponent;
  /** CSS color（原仓 tailwind tint 类的等价值）。 */
  tint: string;
  label: string; // e.g. "PDF"
}

// Extension → icon category. Grouped so we get meaningful visual differentiation
// without carrying 50 distinct icons.
const CODE_EXTS = new Set([
  // JS/TS
  ".js",
  ".mjs",
  ".cjs",
  ".ts",
  ".mts",
  ".cts",
  ".jsx",
  ".tsx",
  ".vue",
  ".svelte",
  // Python
  ".py",
  // JVM
  ".java",
  ".kt",
  ".kts",
  ".scala",
  ".groovy",
  ".gradle",
  // Systems
  ".c",
  ".h",
  ".cpp",
  ".cc",
  ".cxx",
  ".hpp",
  ".hh",
  ".hxx",
  ".cs",
  ".go",
  ".rs",
  ".zig",
  ".nim",
  // Apple
  ".swift",
  ".m",
  ".mm",
  // Scripting
  ".rb",
  ".php",
  ".pl",
  ".pm",
  ".lua",
  ".r",
  ".jl",
  ".dart",
  // Functional
  ".hs",
  ".clj",
  ".cljs",
  ".cljc",
  ".ex",
  ".exs",
  ".erl",
  ".ml",
  ".mli",
  ".fs",
  ".fsx",
  ".lisp",
  ".lsp",
  ".scm",
  ".rkt",
  // Smart contracts
  ".sol",
]);
const SHELL_EXTS = new Set([
  ".sh",
  ".bash",
  ".zsh",
  ".fish",
  ".ps1",
  ".vim",
  ".sql",
]);
const CONFIG_EXTS = new Set([
  ".yaml",
  ".yml",
  ".toml",
  ".ini",
  ".cfg",
  ".conf",
  ".env",
  ".properties",
  ".tf",
  ".hcl",
  ".nginxconf",
  ".cmake",
  ".mk",
  ".dockerfile",
]);
const JSON_EXTS = new Set([".json", ".jsonc", ".json5"]);
const MARKUP_EXTS = new Set([
  ".md",
  ".markdown",
  ".rst",
  ".asciidoc",
  ".html",
  ".htm",
  ".xml",
  ".tex",
  ".latex",
  ".bib",
  ".graphql",
  ".gql",
  ".proto",
]);
const DATA_EXTS = new Set([".csv", ".tsv"]);
const STYLE_EXTS = new Set([".css", ".scss", ".sass", ".less"]);
const PLAIN_EXTS = new Set([".txt", ".text", ".log"]);

export function docIconFor(filename: string): DocIconSpec {
  const ext = extOf(filename);
  // Office first — keep the original distinctive colors
  switch (ext) {
    case ".pdf":
      return {
        Icon: FilePdfOutlined,
        tint: "rgba(239, 68, 68, 0.8)",
        label: "PDF",
      };
    case ".docx":
      return {
        Icon: FileTextOutlined,
        tint: "rgba(59, 130, 246, 0.8)",
        label: "DOCX",
      };
    case ".xlsx":
      return {
        Icon: FileExcelOutlined,
        tint: "rgba(16, 185, 129, 0.8)",
        label: "XLSX",
      };
    case ".pptx":
      return {
        Icon: FilePptOutlined,
        tint: "rgba(249, 115, 22, 0.8)",
        label: "PPTX",
      };
    case ".svg":
      return {
        Icon: FileImageOutlined,
        tint: "rgba(20, 184, 166, 0.8)",
        label: "SVG",
      };
  }
  const label = ext ? ext.slice(1).toUpperCase() : "FILE";
  if (CODE_EXTS.has(ext)) {
    return { Icon: CodeOutlined, tint: "rgba(139, 92, 246, 0.8)", label };
  }
  if (SHELL_EXTS.has(ext)) {
    return { Icon: MacCommandOutlined, tint: "rgba(100, 116, 139, 0.8)", label };
  }
  if (JSON_EXTS.has(ext)) {
    return { Icon: ApiOutlined, tint: "rgba(245, 158, 11, 0.8)", label };
  }
  if (CONFIG_EXTS.has(ext)) {
    return { Icon: SettingOutlined, tint: "rgba(100, 116, 139, 0.8)", label };
  }
  if (STYLE_EXTS.has(ext)) {
    return { Icon: BgColorsOutlined, tint: "rgba(236, 72, 153, 0.8)", label };
  }
  if (DATA_EXTS.has(ext)) {
    return { Icon: FileExcelOutlined, tint: "rgba(52, 211, 153, 0.8)", label };
  }
  if (MARKUP_EXTS.has(ext)) {
    return { Icon: CodeOutlined, tint: "rgba(14, 165, 233, 0.8)", label };
  }
  if (PLAIN_EXTS.has(ext)) {
    return {
      Icon: FileTextOutlined,
      tint: "var(--muted-foreground, #64748b)",
      label,
    };
  }
  // Unknown text-ish file — neutral fallback
  return {
    Icon: FileAddOutlined,
    tint: "var(--muted-foreground, #64748b)",
    label,
  };
}
