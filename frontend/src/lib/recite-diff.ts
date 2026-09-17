/**
 * recite-diff — 背诵/默写判分的前端展示纯函数（M25 三年级上批次 T14，
 * 规格 §9：matcher 前端展示逻辑 / diff 分类着色）。
 *
 * 与后端判分（deeptutor/learning/recitation/matcher.py）解耦：后端返回
 * 错字/同音/漏/多 四类清单，前端把差异段统一映射为五类着色分类
 * （✅绿 ok / 🔴红 wrong / 🟡黄 homophone / ➖灰 missing / ➕蓝 extra），
 * 桌面（T12 ReciteTab）与 H5（T13 双端 1:1）共用同一映射。
 */

export type DiffType = "equal" | "wrong" | "homophone" | "missing" | "extra";
export type DiffCls = "ok" | "wrong" | "homophone" | "missing" | "extra";

export interface DiffSegIn {
  type: DiffType;
  text: string;
}

export interface DiffSegOut {
  text: string;
  cls: DiffCls;
}

/** type → cls 映射（equal 判定为 ok，其余同名直映）。 */
const CLS_BY_TYPE: Record<DiffType, DiffCls> = {
  equal: "ok",
  wrong: "wrong",
  homophone: "homophone",
  missing: "missing",
  extra: "extra",
};

/** diff 段列表 → {text, cls} 着色分类（顺序与文本原样透传）。 */
export function classifySegments(segments: DiffSegIn[]): DiffSegOut[] {
  return segments.map((s) => ({ text: s.text, cls: CLS_BY_TYPE[s.type] ?? s.type }));
}

/**
 * 分数展示：(正确+同音)/总数 取整为百分号字符串（与后端 score 口径
 * 一致——同音计入得分）。total=0 → "0%"（防除零）。
 */
export function scoreLabel(c: { correct: number; homophone: number; total: number }): string {
  if (!c.total) return "0%";
  const pct = Math.round(((c.correct + c.homophone) / c.total) * 100);
  return `${Math.max(0, Math.min(100, pct))}%`;
}

/**
 * cls → tailwind 着色类（五类互异）：ok 绿 / wrong 红 / homophone 黄 /
 * missing 灰 / extra 蓝。与 ReciteTab 结果视图的边框+底色口径对齐。
 */
export function segmentClass(cls: DiffCls): string {
  switch (cls) {
    case "ok":
      return "border-green-300 bg-green-50 text-green-700";
    case "wrong":
      return "border-red-300 bg-red-50 text-red-600";
    case "homophone":
      return "border-amber-300 bg-amber-50 text-amber-600";
    case "missing":
      return "border-slate-300 bg-slate-50 text-slate-600";
    case "extra":
      return "border-blue-300 bg-blue-50 text-blue-600";
  }
}
