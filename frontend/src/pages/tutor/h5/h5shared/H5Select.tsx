/**
 * S2（M23）：H5Select —— 原生 select 的移动端包装——原仓 1:1 移植。
 * 设计约定：
 *  - 原生 select 保留（iOS/Android 系统选择器最优，桌面仍有下拉）
 *  - 44px 最小触点高度；聚焦时字号 ≥16px（配合全局 .dsh-h5 规则防 iOS 缩放）
 *  - option 带 title（长文本悬浮可见）
 */
export function H5Select({
  value,
  onChange,
  options,
  placeholder,
  ariaLabel,
  testId,
}: {
  value: string | number;
  onChange: (value: string) => void;
  options: Array<{ value: string | number; label: string }>;
  placeholder?: string;
  ariaLabel?: string;
  testId?: string;
}) {
  return (
    <select
      value={String(value)}
      onChange={(e) => onChange(e.target.value)}
      aria-label={ariaLabel}
      data-testid={testId}
      style={{
        width: "100%", minHeight: 44, padding: "8px 12px", borderRadius: 12,
        border: "1px solid #e2e8f0", fontSize: 14, background: "#fff",
        appearance: "none", boxSizing: "border-box",
      }}
    >
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)} title={o.label}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
