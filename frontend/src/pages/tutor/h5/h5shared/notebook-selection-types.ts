/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/lib/notebook-selection-types.ts，40 行）。
 * 后续批可迁位。替换点：getTypeColor 原返回 Tailwind 类串（tupu 无 Tailwind），
 * 改为返回等价内联样式对象（bg-*-100/text-*-700/border-*-200 → 十六进制），
 * 本批 NotebookSelector/NotebookRecordPicker 消费侧同步对位；其余类型逐字未改。
 */

// Shared types used by Notebook reference pickers.

export interface Notebook {
  id: string;
  name: string;
  description: string;
  record_count: number;
  color: string;
}

export interface NotebookRecord {
  id: string;
  title: string;
  summary?: string;
  user_query: string;
  output: string;
  type: string;
}

export interface SelectedRecord extends NotebookRecord {
  notebookId: string;
  notebookName: string;
}

export function getTypeColor(type: string): {
  background: string;
  color: string;
  borderColor: string;
} {
  switch (type) {
    case "solve":
      return { background: "#dbeafe", color: "#1d4ed8", borderColor: "#bfdbfe" };
    case "question":
      return { background: "#f3e8ff", color: "#6d28d9", borderColor: "#e9d5ff" };
    case "research":
      return { background: "#d1fae5", color: "#047857", borderColor: "#a7f3d0" };
    case "chat":
      return { background: "#cffafe", color: "#0e7490", borderColor: "#a5f3fc" };
    case "co_writer":
      return { background: "#fef3c7", color: "#b45309", borderColor: "#fde68a" };
    default:
      return { background: "#f1f5f9", color: "#334155", borderColor: "#e2e8f0" };
  }
}
