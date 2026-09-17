/**
 * 工具设置（1:1 复刻自原仓 web/app/(utility)/settings/tools/page.tsx）：
 * 按体验增强 / 内置工具 / 能力专属工具 分组列出 chat agent 工具——
 * 可开关工具（乐观更新 + 失败回滚 + 缓存失效）、始终启用徽标、敬请期待锁定、
 * 展开详情（何时使用/输入格式/使用指引/笔记/参数表）。
 * ToolToggle → antd Switch；apiFetch/apiUrl → 相对路径 fetch；
 * invalidateEnabledOptionalToolsCache 复用本仓复刻件（../tutor/h5/h5shared/toolsSettings）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Spin, Switch } from 'antd';
import { DownOutlined, LoadingOutlined, LockOutlined, ToolOutlined } from '@ant-design/icons';
import { useSettings } from '../../components/settings/SettingsContext';
import { SettingsPageHeader } from '../../components/settings/shared';
import { invalidateEnabledOptionalToolsCache } from '../tutor/h5/h5shared/toolsSettings';

type ToolParameter = {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default: unknown;
  enum: string[] | null;
};

type ToolHints = {
  short_description: string;
  when_to_use: string;
  input_format: string;
  guideline: string;
  note: string;
  phase: string;
  aliases: { name: string; description: string; phase: string }[];
};

type BuiltinTool = {
  name: string;
  description: string;
  parameters: ToolParameter[];
  hints: { en: ToolHints; zh: ToolHints };
  aliases: string[];
  toggleable: boolean;
  enabled: boolean;
  // ``coming_soon`` tools are listed for visibility but the chat agent
  // cannot invoke them. The settings UI surfaces them with a locked-off
  // toggle and a "Coming soon" badge.
  coming_soon?: boolean;
  // The capability that owns this tool (e.g. "solve" / "mastery"), or null
  // for a plain system built-in. Owned tools render in their own section
  // below the built-in tools.
  capability?: string | null;
};

type ToolsResponse = {
  tools: BuiltinTool[];
  enabled_optional_tools: string[];
};

type ToolSection = {
  key: string;
  label: string;
  hint: string;
  tools: BuiltinTool[];
};

// Display labels for capability-owned tool sections, keyed by the backend's
// capability id. Falls back to the raw id for any unmapped capability.
const CAPABILITY_LABELS: Record<string, { zh: string; en: string }> = {
  solve: { zh: '深度解题', en: 'Deep Solve' },
  mastery: { zh: '精通路径', en: 'Mastery Path' },
};

export default function ToolsSettingsPage() {
  const { language } = useSettings();
  const lang: 'en' | 'zh' = language === 'zh' ? 'zh' : 'en';
  const [tools, setTools] = useState<BuiltinTool[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [enabled, setEnabled] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch('/api/v1/tools');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = (await res.json()) as ToolsResponse;
        if (!cancelled) {
          setTools(payload.tools);
          setEnabled(new Set(payload.enabled_optional_tools ?? []));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const persist = useCallback(async (next: Set<string>) => {
    const body = JSON.stringify({ enabled_tools: Array.from(next) });
    const res = await fetch('/api/v1/settings/enabled-tools', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = (await res.json()) as { enabled_optional_tools: string[] };
    // Bust the cached snapshot any other page in this tab is holding.
    invalidateEnabledOptionalToolsCache();
    return new Set(payload.enabled_optional_tools);
  }, []);

  const handleToggleEnabled = useCallback(
    async (toolName: string) => {
      if (pending.has(toolName)) return;
      const before = enabled;
      const next = new Set(before);
      if (next.has(toolName)) next.delete(toolName);
      else next.add(toolName);
      setEnabled(next);
      setPending((prev) => new Set(prev).add(toolName));
      setSaveError(null);
      try {
        const saved = await persist(next);
        setEnabled(saved);
      } catch (err) {
        setEnabled(before);
        setSaveError(err instanceof Error ? err.message : String(err));
      } finally {
        setPending((prev) => {
          const out = new Set(prev);
          out.delete(toolName);
          return out;
        });
      }
    },
    [enabled, pending, persist],
  );

  const sections = useMemo<ToolSection[] | null>(() => {
    if (!tools) return null;
    const zh = language === 'zh';
    // Buckets: toggleable (体验增强) first, then locked-on built-ins, then one
    // section per capability for its owned tools. Backend order is preserved
    // within each bucket (mirrors USER_TOGGLEABLE_TOOL_NAMES / the
    // BUILTIN_TOOL_TYPES registration order). Coming-soon tools share the
    // toggleable bucket — same concept, just temporarily unavailable.
    const experience: BuiltinTool[] = [];
    const builtin: BuiltinTool[] = [];
    const capabilities = new Map<string, BuiltinTool[]>();
    for (const tool of tools) {
      if (tool.capability) {
        const list = capabilities.get(tool.capability) ?? [];
        list.push(tool);
        capabilities.set(tool.capability, list);
      } else if (tool.coming_soon) {
        experience.push(tool);
      } else {
        (tool.toggleable ? experience : builtin).push(tool);
      }
    }
    const out: ToolSection[] = [];
    if (experience.length) {
      out.push({
        key: 'experience',
        label: zh ? '体验增强' : 'Experience Enhancement',
        hint: zh
          ? '用户可选；按需为 chat agent 开启或关闭。'
          : 'User-toggleable. Switch on or off to shape the chat agent\'s behavior.',
        tools: experience,
      });
    }
    if (builtin.length) {
      out.push({
        key: 'builtin',
        label: zh ? '内置工具' : 'Built-in Tools',
        hint: zh
          ? 'Chat agent 在需要时自动挂载，无需手动开关。'
          : 'Mounted automatically by the chat agent when needed. Not user-toggleable.',
        tools: builtin,
      });
    }
    for (const [cap, list] of Array.from(capabilities)) {
      const label = CAPABILITY_LABELS[cap]?.[zh ? 'zh' : 'en'] ?? cap;
      out.push({
        key: `cap:${cap}`,
        label: zh ? `${label} · 能力工具` : `${label} · Capability Tools`,
        hint: zh
          ? '该能力的专属工具，仅在此能力运行时挂载。'
          : 'Tools specific to this capability; mounted only when it runs.',
        tools: list,
      });
    }
    return out;
  }, [tools, language]);

  const toggleExpanded = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <div data-tour="tour-tools" data-testid="settings-page-tools">
      <SettingsPageHeader
        title="工具"
        testId="settings-tools-header"
        description="在此开关用户可自选的工具；锁定工具会在 chat agent 需要时自动挂载。"
      />

      {error && (
        <div
          data-testid="tools-error"
          style={{
            borderRadius: 12,
            border: '1px solid rgba(255, 77, 79, 0.4)',
            background: 'rgba(255, 77, 79, 0.05)',
            padding: '12px 16px',
            fontSize: 12,
            color: '#ff4d4f',
          }}
        >
          加载工具列表失败: {error}
        </div>
      )}

      {saveError && (
        <div
          data-testid="tools-save-error"
          style={{
            marginBottom: 16,
            borderRadius: 12,
            border: '1px solid rgba(255, 77, 79, 0.4)',
            background: 'rgba(255, 77, 79, 0.05)',
            padding: '12px 16px',
            fontSize: 12,
            color: '#ff4d4f',
          }}
        >
          保存失败: {saveError}
        </div>
      )}

      {!tools && !error && (
        <div
          data-testid="tools-loading"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 12,
            color: 'rgba(0, 0, 0, 0.45)',
          }}
        >
          <Spin indicator={<LoadingOutlined spin />} />
          加载中…
        </div>
      )}

      {sections && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
          {sections.map((section) => {
            const list = section.tools;
            if (list.length === 0) return null;
            return (
              <section key={section.key} data-testid={`tools-section-${section.key}`}>
                <header style={{ marginBottom: 12, display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ minWidth: 0 }}>
                    <h2 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: 'rgba(0, 0, 0, 0.88)' }}>
                      {section.label}
                    </h2>
                    <p style={{ margin: '2px 0 0', fontSize: 11.5, color: 'rgba(0, 0, 0, 0.45)' }}>
                      {section.hint}
                    </p>
                  </div>
                  <span style={{ flexShrink: 0, fontSize: 11, color: 'rgba(0, 0, 0, 0.45)' }}>
                    {list.length}
                  </span>
                </header>
                <div
                  style={{
                    overflow: 'hidden',
                    borderRadius: 12,
                    border: '1px solid rgba(0, 0, 0, 0.06)',
                    background: 'rgba(255, 255, 255, 0.4)',
                  }}
                >
                  {list.map((tool, idx) => {
                    const isOpen = expanded.has(tool.name);
                    const hints = tool.hints[lang];
                    const isPending = pending.has(tool.name);
                    const isComingSoon = !!tool.coming_soon;
                    const isEnabled =
                      !isComingSoon &&
                      (tool.toggleable ? enabled.has(tool.name) : true);
                    return (
                      <div
                        key={tool.name}
                        data-testid={`tools-tool-${tool.name}`}
                        data-expanded={isOpen || undefined}
                        style={
                          idx > 0
                            ? { borderTop: '1px solid rgba(0, 0, 0, 0.05)' }
                            : undefined
                        }
                      >
                        <div style={{ display: 'flex', width: '100%', alignItems: 'flex-start', gap: 12, padding: '16px 20px' }}>
                          <ToolOutlined
                            style={{
                              marginTop: 2,
                              flexShrink: 0,
                              color: isComingSoon
                                ? 'rgba(0, 0, 0, 0.15)'
                                : 'rgba(0, 0, 0, 0.45)',
                            }}
                          />
                          <button
                            type="button"
                            onClick={() => toggleExpanded(tool.name)}
                            data-testid={`tools-tool-${tool.name}-expand`}
                            style={{
                              display: 'flex',
                              minWidth: 0,
                              flex: 1,
                              alignItems: 'flex-start',
                              gap: 12,
                              textAlign: 'left',
                              background: 'none',
                              border: 'none',
                              padding: 0,
                              cursor: 'pointer',
                            }}
                            aria-expanded={isOpen}
                          >
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span
                                  style={{
                                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                                    fontSize: 13,
                                    fontWeight: 500,
                                    color: isComingSoon
                                      ? 'rgba(0, 0, 0, 0.5)'
                                      : 'rgba(0, 0, 0, 0.88)',
                                  }}
                                >
                                  {tool.name}
                                </span>
                                {tool.aliases.length > 0 && (
                                  <span style={{ fontSize: 10.5, color: 'rgba(0, 0, 0, 0.35)' }}>
                                    {tool.aliases.join(' · ')}
                                  </span>
                                )}
                                {isComingSoon && (
                                  <span
                                    style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: 4,
                                      borderRadius: 999,
                                      border: '1px solid #f0f0f0',
                                      background: 'rgba(0, 0, 0, 0.03)',
                                      padding: '2px 8px',
                                      fontSize: 10,
                                      fontWeight: 500,
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em',
                                      color: 'rgba(0, 0, 0, 0.45)',
                                    }}
                                  >
                                    {language === 'zh' ? '敬请期待' : 'Coming soon'}
                                  </span>
                                )}
                              </div>
                              <p
                                style={{
                                  marginTop: 4,
                                  marginBottom: 0,
                                  fontSize: 12.5,
                                  lineHeight: 1.625,
                                  color: isComingSoon
                                    ? 'rgba(0, 0, 0, 0.35)'
                                    : 'rgba(0, 0, 0, 0.45)',
                                }}
                              >
                                {hints.short_description || tool.description}
                              </p>
                            </div>
                            <DownOutlined
                              style={{
                                marginTop: 4,
                                flexShrink: 0,
                                fontSize: 12,
                                color: 'rgba(0, 0, 0, 0.45)',
                                transition: 'transform 0.2s',
                                transform: isOpen ? 'rotate(180deg)' : 'none',
                              }}
                            />
                          </button>
                          <div style={{ marginTop: 2, display: 'flex', flexShrink: 0, alignItems: 'center', gap: 8 }}>
                            {isComingSoon ? (
                              <ToolToggle
                                checked={false}
                                disabled
                                onChange={() => {
                                  /* locked */
                                }}
                                label={language === 'zh' ? '敬请期待' : 'Coming soon'}
                                testId={`tools-toggle-${tool.name}`}
                              />
                            ) : tool.toggleable ? (
                              <ToolToggle
                                checked={isEnabled}
                                disabled={isPending}
                                onChange={() => void handleToggleEnabled(tool.name)}
                                label={isEnabled ? '已启用' : '已关闭'}
                                testId={`tools-toggle-${tool.name}`}
                              />
                            ) : (
                              <span
                                data-testid={`tools-always-on-${tool.name}`}
                                title="由 agent 在需要时自动挂载，用户无需手动开关。"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                  borderRadius: 999,
                                  background: 'rgba(0, 0, 0, 0.03)',
                                  padding: '2px 8px',
                                  fontSize: 10.5,
                                  color: 'rgba(0, 0, 0, 0.45)',
                                }}
                              >
                                <LockOutlined style={{ fontSize: 12 }} />
                                始终启用
                              </span>
                            )}
                          </div>
                        </div>
                        {isOpen && (
                          <div
                            data-testid={`tools-details-${tool.name}`}
                            style={{
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 16,
                              borderTop: '1px solid rgba(0, 0, 0, 0.04)',
                              background: 'rgba(0, 0, 0, 0.01)',
                              padding: '16px 20px',
                              fontSize: 12.5,
                              lineHeight: 1.625,
                            }}
                          >
                            {hints.when_to_use && (
                              <Field label="何时使用" body={hints.when_to_use} />
                            )}
                            {hints.input_format && (
                              <Field label="输入格式" body={hints.input_format} mono />
                            )}
                            {hints.guideline && (
                              <Field label="使用指引" body={hints.guideline} />
                            )}
                            {hints.note && <Field label="笔记" body={hints.note} />}
                            {tool.parameters.length > 0 && (
                              <div>
                                <div
                                  style={{
                                    marginBottom: 4,
                                    fontSize: 10.5,
                                    fontWeight: 600,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.14em',
                                    color: 'rgba(0, 0, 0, 0.35)',
                                  }}
                                >
                                  参数
                                </div>
                                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                                  {tool.parameters.map((p) => (
                                    <li
                                      key={p.name}
                                      style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}
                                    >
                                      <span
                                        style={{
                                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                                          fontSize: 12,
                                          color: 'rgba(0, 0, 0, 0.88)',
                                        }}
                                      >
                                        {p.name}
                                      </span>
                                      <span style={{ fontSize: 10.5, color: 'rgba(0, 0, 0, 0.35)' }}>
                                        {p.type}
                                        {p.required ? '' : ` · 可选`}
                                      </span>
                                      {p.description && (
                                        <span style={{ fontSize: 12, color: 'rgba(0, 0, 0, 0.45)' }}>
                                          — {p.description}
                                        </span>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ToolToggle({
  checked,
  disabled,
  onChange,
  label,
  testId,
}: {
  checked: boolean;
  disabled: boolean;
  onChange: () => void;
  label: string;
  testId?: string;
}) {
  return (
    <Switch
      checked={checked}
      disabled={disabled}
      onChange={onChange}
      size="small"
    />
  );
}

function Field({
  label,
  body,
  mono,
}: {
  label: string;
  body: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div
        style={{
          marginBottom: 4,
          fontSize: 10.5,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
          color: 'rgba(0, 0, 0, 0.35)',
        }}
      >
        {label}
      </div>
      <p
        style={{
          margin: 0,
          whiteSpace: 'pre-wrap',
          fontSize: 12.5,
          lineHeight: 1.625,
          color: 'rgba(0, 0, 0, 0.8)',
          ...(mono
            ? { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' }
            : {}),
        }}
      >
        {body}
      </p>
    </div>
  );
}
