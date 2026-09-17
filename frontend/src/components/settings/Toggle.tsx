/**
 * 复刻自 DeepTutor 原仓 web/components/settings/Toggle.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：仅样式承载方式——原仓 Tailwind 类（h-5 w-9 / rounded-full / bg-[var(--foreground)]
 * 等）逐项换为内联样式（颜色语义一致：开=前景色、关=边框色，token 值兜底）；
 * 结构/role/aria/data-testid/props 契约逐字保留。
 */
export function Toggle({
  checked,
  onChange,
  disabled,
  testId,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  /** Optional stable selector for e2e audits (data-testid passthrough). */
  testId?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      data-testid={testId}
      style={{
        position: "relative",
        height: 20,
        width: 36,
        flexShrink: 0,
        borderRadius: 9999,
        padding: 0,
        border: "none",
        cursor: disabled ? "default" : "pointer",
        transition: "background-color 150ms",
        opacity: disabled ? 0.4 : 1,
        background: checked
          ? "var(--foreground, #0f172a)"
          : "var(--border, #e2e8f0)",
      }}
    >
      <span
        style={{
          position: "absolute",
          left: 2,
          top: 2,
          height: 16,
          width: 16,
          borderRadius: 9999,
          background: "var(--background, #ffffff)",
          boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
          transition: "transform 150ms",
          transform: checked ? "translateX(16px)" : "translateX(0)",
          display: "block",
        }}
      />
    </button>
  );
}
