// 预览族支持层，移植自源仓三处（1:1 合并）：
//   - web/lib/code-languages.ts（CODE_EXT_TO_LANG / CODE_EXTS / langForFilename）
//   - web/lib/doc-attachments.ts 中的 docIconFor 与伴随图标映射
//     （lucide 图标 → @ant-design/icons 最近等价；局部 CODE_EXTS 与上一条
//      的导出重名，改名 DOC_ICON_CODE_EXTS）
//   - web/components/chat/preview/previewerFor.ts
//     （PreviewKind / FilePreviewSource / previewKindFor / resolveSourceUrl）
// extOf/formatBytes 复用已有移植件 pages/tutor/admin/doc-attachments.ts。
// t() → 中文硬编码（映射表：源仓 locales/zh/app.json）。

import type { ComponentType, CSSProperties } from "react";
import {
  BgColorsOutlined,
  CodeOutlined,
  FileAddOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  FileMarkdownOutlined,
  FilePdfOutlined,
  FilePptOutlined,
  FileTextOutlined,
  FileWordOutlined,
  SettingOutlined,
  SnippetsOutlined,
} from "@ant-design/icons";
import { extOf } from "../tutor/admin/doc-attachments";

/** antd 图标组件的最小形态（等价 lucide 的 LucideIcon 用法）。 */
export type AntdIconComponent = ComponentType<{
  className?: string;
  style?: CSSProperties;
}>;

// ─────────────────────────────────────────────────────────────────────────────
// code-languages.ts — Single source of truth for code-file syntax highlighting.
// ─────────────────────────────────────────────────────────────────────────────

/** Extension (lowercase, with leading dot) → Prism language name. */
export const CODE_EXT_TO_LANG: Record<string, string> = {
  // Mainstream
  ".py": "python",
  ".js": "javascript",
  ".mjs": "javascript",
  ".cjs": "javascript",
  ".ts": "typescript",
  ".mts": "typescript",
  ".cts": "typescript",
  ".jsx": "jsx",
  ".tsx": "tsx",
  ".java": "java",
  ".kt": "kotlin",
  ".kts": "kotlin",
  ".scala": "scala",
  ".groovy": "groovy",
  ".gradle": "groovy",

  // Systems
  ".c": "c",
  ".h": "c",
  ".cpp": "cpp",
  ".cc": "cpp",
  ".cxx": "cpp",
  ".hpp": "cpp",
  ".hh": "cpp",
  ".hxx": "cpp",
  ".cs": "csharp",
  ".go": "go",
  ".rs": "rust",
  ".zig": "zig",
  ".nim": "nim",

  // Apple platforms
  ".swift": "swift",
  ".m": "objectivec",
  ".mm": "objectivec",

  // Scripting
  ".rb": "ruby",
  ".php": "php",
  ".pl": "perl",
  ".pm": "perl",
  ".lua": "lua",
  ".r": "r",
  ".jl": "julia",
  ".dart": "dart",

  // Functional
  ".hs": "haskell",
  ".clj": "clojure",
  ".cljs": "clojure",
  ".cljc": "clojure",
  ".ex": "elixir",
  ".exs": "elixir",
  ".erl": "erlang",
  ".ml": "ocaml",
  ".mli": "ocaml",
  ".fs": "fsharp",
  ".fsx": "fsharp",
  ".lisp": "lisp",
  ".lsp": "lisp",
  ".scm": "scheme",
  ".rkt": "racket",

  // Web frameworks
  ".vue": "markup", // single-file component; Prism's vue plugin not always bundled — markup as a safe fallback
  ".svelte": "markup",

  // Web markup / styles
  ".html": "markup",
  ".htm": "markup",
  ".xml": "markup",
  ".css": "css",
  ".scss": "scss",
  ".sass": "sass",
  ".less": "less",
  ".sol": "solidity",

  // Shells
  ".sh": "bash",
  ".bash": "bash",
  ".zsh": "bash",
  ".fish": "bash",
  ".ps1": "powershell",
  ".vim": "vim",

  // Data / config
  ".json": "json",
  ".jsonc": "json",
  ".json5": "json",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".toml": "toml",
  ".ini": "ini",
  ".cfg": "ini",
  ".properties": "ini",

  // Build / infra
  ".sql": "sql",
  ".graphql": "graphql",
  ".gql": "graphql",
  ".proto": "protobuf",
  ".cmake": "cmake",
  ".mk": "makefile",
  ".dockerfile": "docker",
  ".tf": "hcl",
  ".hcl": "hcl",
  ".nginxconf": "nginx",

  // Typesetting
  ".tex": "latex",
  ".latex": "latex",
  ".bib": "latex",
};

/**
 * Special filenames (no extension or shebang-only). Lowercase comparison.
 * Mapped before extension lookup in ``langForFilename``.
 */
const NAMED_FILES: Record<string, string> = {
  dockerfile: "docker",
  makefile: "makefile",
  cmakelists: "cmake",
  "cmakelists.txt": "cmake",
  rakefile: "ruby",
  gemfile: "ruby",
  vagrantfile: "ruby",
  "nginx.conf": "nginx",
  ".bashrc": "bash",
  ".zshrc": "bash",
  ".bash_profile": "bash",
  ".profile": "bash",
};

/** Set of all extensions covered by ``CODE_EXT_TO_LANG``. */
export const CODE_EXTS: ReadonlySet<string> = new Set(
  Object.keys(CODE_EXT_TO_LANG),
);

/**
 * Resolve a Prism language for *filename*.
 *
 * Looks at the bare filename (e.g. ``Dockerfile``) before falling back to
 * the extension. Returns ``null`` when the file is not a recognised code
 * language — callers should render it as plain monospace text.
 */
export function langForFilename(filename: string): string | null {
  if (!filename) return null;
  const lastSlash = filename.lastIndexOf("/");
  const base = (
    lastSlash >= 0 ? filename.slice(lastSlash + 1) : filename
  ).toLowerCase();
  if (NAMED_FILES[base]) return NAMED_FILES[base];

  const dotIdx = base.lastIndexOf(".");
  if (dotIdx < 0) return null;
  const ext = base.slice(dotIdx);
  return CODE_EXT_TO_LANG[ext] ?? null;
}

// ─────────────────────────────────────────────────────────────────────────────
// doc-attachments.ts（节选）— docIconFor 与伴随图标映射
// ─────────────────────────────────────────────────────────────────────────────

export interface DocIconSpec {
  Icon: AntdIconComponent;
  tint: string; // tailwind class, e.g. "text-red-500/80"
  label: string; // e.g. "PDF"
}

// Extension → icon category. Grouped so we get meaningful visual differentiation
// without carrying 50 distinct icons.
const DOC_ICON_CODE_EXTS = new Set([
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
      return { Icon: FilePdfOutlined, tint: "text-red-500/80", label: "PDF" };
    case ".docx":
      return { Icon: FileWordOutlined, tint: "text-blue-500/80", label: "DOCX" };
    case ".xlsx":
      return {
        Icon: FileExcelOutlined,
        tint: "text-emerald-500/80",
        label: "XLSX",
      };
    case ".pptx":
      return { Icon: FilePptOutlined, tint: "text-orange-500/80", label: "PPTX" };
    case ".svg":
      return { Icon: FileImageOutlined, tint: "text-teal-500/80", label: "SVG" };
  }
  const label = ext ? ext.slice(1).toUpperCase() : "FILE";
  if (DOC_ICON_CODE_EXTS.has(ext)) {
    return { Icon: CodeOutlined, tint: "text-violet-500/80", label };
  }
  if (SHELL_EXTS.has(ext)) {
    return { Icon: CodeOutlined, tint: "text-slate-500/80", label };
  }
  if (JSON_EXTS.has(ext)) {
    return { Icon: SnippetsOutlined, tint: "text-amber-500/80", label };
  }
  if (CONFIG_EXTS.has(ext)) {
    return { Icon: SettingOutlined, tint: "text-slate-500/80", label };
  }
  if (STYLE_EXTS.has(ext)) {
    return { Icon: BgColorsOutlined, tint: "text-pink-500/80", label };
  }
  if (DATA_EXTS.has(ext)) {
    return { Icon: FileExcelOutlined, tint: "text-emerald-400/80", label };
  }
  if (MARKUP_EXTS.has(ext)) {
    return { Icon: FileMarkdownOutlined, tint: "text-sky-500/80", label };
  }
  if (PLAIN_EXTS.has(ext)) {
    return { Icon: FileTextOutlined, tint: "text-[var(--muted-foreground)]", label };
  }
  // Unknown text-ish file — neutral fallback
  return {
    Icon: FileAddOutlined,
    tint: "text-[var(--muted-foreground)]",
    label,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// previewerFor.ts — Maps a chat attachment to the preview renderer it should use.
// ─────────────────────────────────────────────────────────────────────────────

export type PreviewKind =
  | "pdf"
  | "image"
  | "svg"
  | "markdown"
  | "code"
  | "text"
  | "docx"
  | "xlsx"
  | "office-text"
  | "fallback";

export interface FilePreviewSource {
  /** Display name; also used to derive the file extension. */
  filename: string;
  /** MIME type when known (image/png, application/pdf, …). */
  mimeType?: string;
  /** Backend classification — "image" or anything else. Useful for
   *  attachments where the filename has no extension but the MIME is set. */
  type?: string;
  /** Public URL served by /api/attachments. Preferred over base64. */
  url?: string;
  /** Inline base64 payload — only present for pending (un-sent) attachments
   *  or messages that pre-date the storage rollout. */
  base64?: string;
  /** Plain-text rendering of office docs, populated by the backend. */
  extractedText?: string;
  /** Optional endpoint that returns extracted plain text on demand. */
  extractedTextUrl?: string;
  /** Original byte size, used for empty-state copy. */
  size?: number;
  /** Stable id; lets the drawer build a stable React key. */
  id?: string;
}

// OOXML formats with a faithful browser renderer (docx-preview / exceljs).
const DOCX_EXTS = new Set([".docx", ".docm"]);
const XLSX_EXTS = new Set([".xlsx", ".xlsm"]);
// Office binaries with no reliable browser renderer (PowerPoint, and the
// legacy pre-OOXML formats) — fall back to the extractor's plain text.
const OFFICE_BINARY_EXTS = new Set([".pptx", ".ppt", ".doc", ".xls"]);
const MARKDOWN_EXTS = new Set([".md", ".markdown", ".rst", ".asciidoc"]);
const PLAIN_TEXT_EXTS = new Set([
  ".txt",
  ".text",
  ".log",
  ".csv",
  ".tsv",
  ".env",
  ".conf",
]);
const RASTER_IMAGE_EXTS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".bmp",
  ".tif",
  ".tiff",
  ".avif",
]);

/** Heuristic: does *source* refer to an image we can render via <img>? */
function isImage(source: FilePreviewSource, ext: string): boolean {
  if (RASTER_IMAGE_EXTS.has(ext)) return true;
  if (
    source.mimeType?.startsWith("image/") &&
    source.mimeType !== "image/svg+xml"
  )
    return true;
  if (source.type === "image") return true;
  return false;
}

export function previewKindFor(source: FilePreviewSource): PreviewKind {
  const ext = extOf(source.filename || "");
  const mime = source.mimeType || "";

  if (ext === ".pdf" || mime === "application/pdf") return "pdf";
  if (ext === ".svg" || mime === "image/svg+xml") return "svg";
  if (isImage(source, ext)) return "image";
  if (MARKDOWN_EXTS.has(ext) || mime === "text/markdown") return "markdown";
  if (
    DOCX_EXTS.has(ext) ||
    mime ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  )
    return "docx";
  if (
    XLSX_EXTS.has(ext) ||
    mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  )
    return "xlsx";
  if (OFFICE_BINARY_EXTS.has(ext)) return "office-text";
  // Catches both extension-based mappings (.js, .ts, .go, .vue, .lua, …)
  // and special filenames without extensions (Dockerfile, Makefile, …).
  if (langForFilename(source.filename || "")) return "code";
  if (PLAIN_TEXT_EXTS.has(ext) || mime.startsWith("text/")) return "text";
  return "fallback";
}

/**
 * Build the in-browser-loadable URL for the preview, falling back to a
 * data URL when the original file lives only as base64 in memory (the
 * pending-attachment case in the composer).
 *
 * Returns ``null`` when neither is available; renderers should then show a
 * "preview not available" affordance.
 */
export function resolveSourceUrl(
  source: FilePreviewSource,
  apiUrl: (path: string) => string,
): string | null {
  if (source.url) {
    return source.url.startsWith("http") || source.url.startsWith("blob:")
      ? source.url
      : apiUrl(source.url);
  }
  if (source.base64 && source.mimeType) {
    return `data:${source.mimeType};base64,${source.base64}`;
  }
  return null;
}
