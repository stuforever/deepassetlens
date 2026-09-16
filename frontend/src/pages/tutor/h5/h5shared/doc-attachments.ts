/**
 * 批9 扩展件（非整文件新写）：批8 已将 DeepTutor 原仓 web/lib/doc-attachments.ts
 * 复刻为 ../../admin/doc-attachments.ts，但按批8 引用链裁掉了 isSvgFilename 与
 * lucide 图标表 docIconFor/DocIconSpec（原仓 431 行中的 L247-258、L261-431）。
 * 本文件补齐 ChatComposer 引用链所需的这三个导出：
 *   - isSvgFilename：原仓逐字；
 *   - DocIconSpec/docIconFor：lucide → @ant-design/icons 等价替换，tint 类串
 *     （text-*-500/80）→ 等价 rgba 颜色（消费侧由 className 改 style.color）；
 *     分类 Set（CODE/SHELL/CONFIG/JSON/MARKUP/DATA/STYLE/PLAIN）逐字未改。
 * 字面量与基础函数（extOf/classifyFile/formatBytes 等）re-export 批8 件避免双写漂移。
 */
import type { ComponentType, CSSProperties } from "react";
import {
  CodeOutlined,
  FileAddOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  FileMarkdownOutlined,
  FilePdfOutlined,
  FilePptOutlined,
  FileTextOutlined,
  FunctionOutlined,
  SettingOutlined,
  BgColorsOutlined,
} from "@ant-design/icons";

export {
  OFFICE_EXTS,
  TEXT_LIKE_EXTS,
  SUPPORTED_DOC_EXTS,
  SUPPORTED_DOC_MIMES,
  DEFAULT_MAX_ATTACHMENT_BYTES,
  DEFAULT_MAX_TOTAL_ATTACHMENT_BYTES,
  ATTACHMENT_ACCEPT,
  extOf,
  classifyFile,
  formatBytes,
} from "../../admin/doc-attachments";
export type { FileKind } from "../../admin/doc-attachments";

/** Whether a filename refers to an SVG (case-insensitive). */
export function isSvgFilename(filename: string): boolean {
  return extOfLocal(filename) === ".svg";
}

// 本文件自持一份 extOf 引用（re-export 的符号不能在本模块作用域直接可见）。
import { extOf as extOfLocal } from "../../admin/doc-attachments";

export interface DocIconSpec {
  Icon: ComponentType<{ className?: string; style?: CSSProperties }>;
  tint: string; // rgba 颜色串（原为 tailwind 类串，消费侧 style.color）
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
  const ext = extOfLocal(filename);
  // Office first — keep the original distinctive colors
  switch (ext) {
    case ".pdf":
      return {
        Icon: FilePdfOutlined,
        tint: "rgba(239,68,68,0.8)",
        label: "PDF",
      };
    case ".docx":
      return {
        Icon: FileTextOutlined,
        tint: "rgba(59,130,246,0.8)",
        label: "DOCX",
      };
    case ".xlsx":
      return {
        Icon: FileExcelOutlined,
        tint: "rgba(16,185,129,0.8)",
        label: "XLSX",
      };
    case ".pptx":
      return {
        Icon: FilePptOutlined,
        tint: "rgba(249,115,22,0.8)",
        label: "PPTX",
      };
    case ".svg":
      return {
        Icon: FileImageOutlined,
        tint: "rgba(20,184,166,0.8)",
        label: "SVG",
      };
  }
  const label = ext ? ext.slice(1).toUpperCase() : "FILE";
  if (CODE_EXTS.has(ext)) {
    return { Icon: CodeOutlined, tint: "rgba(139,92,246,0.8)", label };
  }
  if (SHELL_EXTS.has(ext)) {
    return { Icon: FunctionOutlined, tint: "rgba(100,116,139,0.8)", label };
  }
  if (JSON_EXTS.has(ext)) {
    return { Icon: FileTextOutlined, tint: "rgba(245,158,11,0.8)", label };
  }
  if (CONFIG_EXTS.has(ext)) {
    return { Icon: SettingOutlined, tint: "rgba(100,116,139,0.8)", label };
  }
  if (STYLE_EXTS.has(ext)) {
    return { Icon: BgColorsOutlined, tint: "rgba(236,72,153,0.8)", label };
  }
  if (DATA_EXTS.has(ext)) {
    return { Icon: FileExcelOutlined, tint: "rgba(52,211,153,0.8)", label };
  }
  if (MARKUP_EXTS.has(ext)) {
    return { Icon: FileMarkdownOutlined, tint: "rgba(14,165,233,0.8)", label };
  }
  if (PLAIN_EXTS.has(ext)) {
    return { Icon: FileTextOutlined, tint: "#6b7280", label };
  }
  // Unknown text-ish file — neutral fallback
  return { Icon: FileAddOutlined, tint: "#6b7280", label };
}
