/**
 * 使用面复刻：复刻自 DeepTutor 原仓 web/lib/doc-attachments.ts（431 行）。
 * 仅保留 tupu 引用链上的导出（BookChatPanel/attachment-limits 实际使用）：
 *   OFFICE_EXTS / TEXT_LIKE_EXTS / SUPPORTED_DOC_EXTS / SUPPORTED_DOC_MIMES /
 *   DEFAULT_MAX_ATTACHMENT_BYTES / DEFAULT_MAX_TOTAL_ATTACHMENT_BYTES /
 *   ATTACHMENT_ACCEPT / FileKind / extOf / classifyFile / formatBytes。
 * 未被引用的 lucide 图标表（docIconFor/DocIconSpec）与 isSvgFilename 已裁剪
 * （避免引入 lucide-react）；其余常量与函数体逐字未改。
 *
 * Helpers for drag-and-drop document attachments in the chat composer.
 *
 * The accepted extension / MIME sets MUST stay in sync with the backend
 * `deeptutor/utils/document_extractor.py` (which in turn mirrors the KB
 * pipeline's `FileTypeRouter.TEXT_EXTENSIONS`). If you add a new format
 * server-side, add it here too.
 */

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

/**
 * Human-readable byte size: `1.2 MB`, `34.0 KB`.
 */
export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
