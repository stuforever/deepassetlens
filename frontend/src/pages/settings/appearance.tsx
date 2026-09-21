/**
 * 外观设置（1:1 复刻自原仓 web/app/(utility)/settings/appearance/page.tsx）：
 * 界面语言（en/zh 分段按钮）、代码块
 * （实时预览 + 语法主题下拉 + 行号开关 + 长行换行开关）。
 * next/dynamic RichCodeBlock → 本文件内联 pre 预览（等价 antd 重建）；
 * CODE_BLOCK_THEME_OPTIONS 内联（原 @/components/common/code-block-themes 选项表）。
 */
import React from 'react';
import { Col, Row, Select } from 'antd';
import { useSettings } from '../../components/settings/SettingsContext';
import {
  SettingRow,
  SettingSection,
  SettingsPageHeader,
} from '../../components/settings/shared';
import { Toggle } from '../../components/settings/Toggle';

type CodeBlockThemeId = string;

// 与原仓 components/common/code-block-themes.ts 的选项表逐项一致（label 原样）。
const CODE_BLOCK_THEME_OPTIONS: { id: CodeBlockThemeId; label: string }[] = [
  { id: 'a11yDark', label: 'A11Y Dark' },
  { id: 'a11yOneLight', label: 'A11Y One Light' },
  { id: 'atomDark', label: 'Atom Dark' },
  { id: 'base16AteliersulphurpoolLight', label: 'Base16 Atelier Sulphurpool Light' },
  { id: 'cb', label: 'CB' },
  { id: 'coldarkCold', label: 'Coldark Cold' },
  { id: 'coldarkDark', label: 'Coldark Dark' },
  { id: 'coyWithoutShadows', label: 'Coy Without Shadows' },
  { id: 'coy', label: 'Coy' },
  { id: 'darcula', label: 'Darcula' },
  { id: 'dark', label: 'Dark' },
  { id: 'dracula', label: 'Dracula' },
  { id: 'duotoneDark', label: 'Duotone Dark' },
  { id: 'duotoneEarth', label: 'Duotone Earth' },
  { id: 'duotoneForest', label: 'Duotone Forest' },
  { id: 'duotoneLight', label: 'Duotone Light' },
  { id: 'duotoneSea', label: 'Duotone Sea' },
  { id: 'duotoneSpace', label: 'Duotone Space' },
  { id: 'funky', label: 'Funky' },
  { id: 'ghcolors', label: 'GH Colors' },
  { id: 'gruvboxDark', label: 'Gruvbox Dark' },
  { id: 'gruvboxLight', label: 'Gruvbox Light' },
  { id: 'holiTheme', label: 'Holi Theme' },
  { id: 'hopscotch', label: 'Hopscotch' },
  { id: 'lucario', label: 'Lucario' },
  { id: 'materialDark', label: 'Material Dark' },
  { id: 'materialLight', label: 'Material Light' },
  { id: 'materialOceanic', label: 'Material Oceanic' },
  { id: 'nightOwl', label: 'Night Owl' },
  { id: 'nord', label: 'Nord' },
  { id: 'okaidia', label: 'Okaidia' },
  { id: 'oneDark', label: 'One Dark' },
  { id: 'oneLight', label: 'One Light' },
  { id: 'pojoaque', label: 'Pojoaque' },
  { id: 'prism', label: 'Prism' },
  { id: 'shadesOfPurple', label: 'Shades of Purple' },
  { id: 'solarizedDarkAtom', label: 'Solarized Dark Atom' },
  { id: 'solarizedlight', label: 'Solarized Light' },
  { id: 'synthwave84', label: 'Synthwave 84' },
  { id: 'tomorrow', label: 'Tomorrow' },
  { id: 'twilight', label: 'Twilight' },
  { id: 'vsDark', label: 'VS Dark' },
  { id: 'vs', label: 'VS' },
  { id: 'vscDarkPlus', label: 'VSC Dark Plus' },
  { id: 'xonokai', label: 'Xonokai' },
  { id: 'zTouch', label: 'Z Touch' },
];

const CODE_BLOCK_PREVIEW_SNIPPET = `def fibonacci(n):
    """Generate the first n Fibonacci numbers."""
    a, b = 0, 1
    result = []
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result


# Build a deliberately long summary so the wrapping preference is easy to see
summary = f"First twenty Fibonacci values rendered with the selected syntax theme, line-number setting, and wrapping preference: {', '.join(str(value) for value in fibonacci(20))}"
print(summary)
`;

const previewPreStyle: React.CSSProperties = {
  margin: 0,
  padding: '12px 16px',
  borderRadius: 8,
  border: '1px solid #f0f0f0',
  background: '#f6f8fa',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  fontSize: 12,
  lineHeight: 1.6,
  overflowX: 'auto',
  whiteSpace: 'pre',
  color: 'rgba(0, 0, 0, 0.88)',
};

export default function AppearanceSettingsPage() {
  const {
    language,
    codeBlockTheme,
    codeBlockShowLineNumbers,
    codeBlockWrapLongLines,
    updateLanguage,
    updateCodeBlockTheme,
    updateCodeBlockShowLineNumbers,
    updateCodeBlockWrapLongLines,
  } = useSettings();

  // All code-block values come straight from the settings context (backed by
  // AppShellContext, the single source of truth), so the toggles reflect the
  // current preference without any local mirror state.
  const handleShowLineNumbersChange = (next: boolean) => {
    void updateCodeBlockShowLineNumbers(next);
  };

  const handleWrapLongLinesChange = (next: boolean) => {
    void updateCodeBlockWrapLongLines(next);
  };

  return (
    <div data-tour="tour-appearance" data-testid="settings-page-appearance">
      <SettingsPageHeader
        title="外观"
        testId="settings-appearance-header"
        description="调整视觉主题和界面语言。改动立即生效并保存到你的账号。"
      />

      <SettingSection
        title="语言"
        testId="appearance-section-language"
        description="选择界面语言。"
      >
        <SettingRow
          title="界面语言"
          testId="appearance-row-language"
          description="只影响界面文案，模型输出语言由你的提示词控制。"
          control={
            <div
              data-testid="appearance-language-group"
              style={{
                display: 'flex',
                gap: 2,
                borderRadius: 8,
                background: 'rgba(0, 0, 0, 0.04)',
                padding: 2,
              }}
            >
              {(['en', 'zh'] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => updateLanguage(v)}
                  data-testid={`appearance-lang-${v}`}
                  data-active={language === v || undefined}
                  style={{
                    borderRadius: 6,
                    padding: '4px 10px',
                    fontSize: 12,
                    border: 'none',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    ...(language === v
                      ? {
                          background: '#fff',
                          fontWeight: 500,
                          color: 'rgba(0, 0, 0, 0.88)',
                          boxShadow: '0 1px 2px rgba(0, 0, 0, 0.06)',
                        }
                      : {
                          background: 'transparent',
                          color: 'rgba(0, 0, 0, 0.45)',
                        }),
                  }}
                >
                  {v === 'en' ? 'English' : '中文'}
                </button>
              ))}
            </div>
          }
        />
      </SettingSection>

      <SettingSection
        title="Code blocks"
        testId="appearance-section-codeblocks"
        description="Choose how code snippets look across the app. Changes apply immediately to saved and streamed responses."
      >
        <div
          style={{
            borderTop: '1px solid rgba(0, 0, 0, 0.04)',
            padding: '16px 4px',
          }}
        >
          <div style={{ fontSize: 13.5, fontWeight: 500, color: 'rgba(0, 0, 0, 0.88)' }}>
            预览
          </div>
          <p
            style={{
              marginBottom: 12,
              marginTop: 4,
              fontSize: 12,
              lineHeight: 1.625,
              color: 'rgba(0, 0, 0, 0.45)',
            }}
          >
            修改下方设置时预览会实时更新。
          </p>
          {/* RichCodeBlock（next/dynamic, ssr:false）→ 内联 pre 预览 */}
          <pre style={previewPreStyle}>{CODE_BLOCK_PREVIEW_SNIPPET}</pre>
        </div>

        <SettingRow
          title="Syntax theme"
          testId="appearance-row-code-theme"
          description="Select the Prism theme used for highlighted code blocks."
          control={
            <Select
              value={codeBlockTheme}
              onChange={(value) =>
                void updateCodeBlockTheme(value as CodeBlockThemeId)
              }
              data-testid="appearance-code-theme-select"
              style={{ minWidth: 220 }}
              options={CODE_BLOCK_THEME_OPTIONS.map((option) => ({
                value: option.id,
                label: option.label,
              }))}
            />
          }
        />

        <SettingRow
          title="Show line numbers"
          testId="appearance-row-line-numbers"
          description="Display a gutter with line numbers beside each code block."
          control={
            <ToggleLineNumbers
              checked={codeBlockShowLineNumbers}
              onChange={handleShowLineNumbersChange}
            />
          }
        />

        <SettingRow
          title="Wrap long lines"
          testId="appearance-row-wrap-lines"
          description="Wrap long code lines instead of forcing horizontal scrolling."
          control={
            <ToggleWrapLines
              checked={codeBlockWrapLongLines}
              onChange={handleWrapLongLinesChange}
            />
          }
        />
      </SettingSection>
    </div>
  );
}

// 小包装：避免 toggle 直接内联时闭包导致 lint/类型噪音（保持源页结构）。
function ToggleLineNumbers({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <Toggle
      checked={checked}
      onChange={onChange}
      testId="appearance-toggle-line-numbers"
    />
  );
}

function ToggleWrapLines({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <Toggle
      checked={checked}
      onChange={onChange}
      testId="appearance-toggle-wrap-lines"
    />
  );
}
