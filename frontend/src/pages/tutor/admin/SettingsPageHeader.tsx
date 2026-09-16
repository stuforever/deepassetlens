/**
 * 设置页头（复刻自原仓 web/components/settings/shared.tsx 的 SettingsPageHeader，
 * 样式语义 1:1：22px 标题 + 13px 描述，Tailwind → 内联样式）。
 */
import React from 'react';

export function SettingsPageHeader({
  title,
  description,
  testId,
}: {
  title: string;
  description?: string;
  /** 可选稳定选择器（e2e 审计 data-testid 透传）。 */
  testId?: string;
}) {
  return (
    <header data-testid={testId} style={{ marginBottom: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em', margin: 0, color: 'rgba(0,0,0,0.88)' }}>
        {title}
      </h1>
      {description && (
        <p style={{ marginTop: 6, marginBottom: 0, fontSize: 13, lineHeight: 1.7, color: 'rgba(0,0,0,0.45)' }}>
          {description}
        </p>
      )}
    </header>
  );
}

export default SettingsPageHeader;
