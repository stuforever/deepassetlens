/**
 * 记忆设置（1:1 复刻自原仓 web/app/(utility)/settings/memory/page.tsx）：
 * Update / Audit / Dedup / Merge footnotes / Chunking / References 六大区
 * （LLM 轮数预算、自动去重/合并、分块重叠比例与边界、引用校验严格度）。
 * 保存走全局 Apply（registerExtension）；NumberRow/ToggleRow/SelectRow 页内实现
 * （antd InputNumber / Switch / 分段按钮组）。
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { InputNumber, Spin, Switch } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import {
  SettingRow,
  SettingSection,
  SettingsPageHeader,
} from '../../components/settings/shared';
import { useSettings } from '../../components/settings/SettingsContext';

interface MemorySettingsDTO {
  update: { l2_budget: number; l3_budget: number };
  audit: { l2_budget: number; l3_budget: number };
  dedup: { iterations: number; auto_after_update: boolean };
  merge: {
    auto_after_update: boolean;
    auto_after_audit: boolean;
    auto_after_dedup: boolean;
  };
  chunking: {
    overlap_ratio: number;
    boundary: 'paragraph' | 'sentence';
    min_chunk_chars: number;
    max_chunk_chars: number;
  };
  reference: {
    enforce_required: boolean;
    drop_invalid_refs: boolean;
  };
}

export default function MemorySettingsPage() {
  const { registerExtension } = useSettings();
  const [settings, setSettings] = useState<MemorySettingsDTO | null>(null);
  const [serverSnapshot, setServerSnapshot] =
    useState<MemorySettingsDTO | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch('/api/v1/memory/settings')
      .then((res) => res.json() as Promise<MemorySettingsDTO>)
      .then((data) => {
        if (cancelled) return;
        setSettings(data);
        setServerSnapshot(data);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty =
    !!settings &&
    !!serverSnapshot &&
    JSON.stringify(settings) !== JSON.stringify(serverSnapshot);

  // Latest-save ref so the closure handed to registerExtension always
  // reflects the current settings without re-registering on each render.
  const settingsRef = useRef<MemorySettingsDTO | null>(null);
  useEffect(() => {
    settingsRef.current = settings;
  }, [settings]);
  const save = useCallback(async () => {
    const current = settingsRef.current;
    if (!current) return;
    const res = await fetch('/api/v1/memory/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(current),
    });
    const data = (await res.json()) as MemorySettingsDTO;
    setSettings(data);
    setServerSnapshot(data);
  }, []);

  useEffect(() => {
    registerExtension('memory', { dirty, save });
    return () => registerExtension('memory', null);
  }, [dirty, save, registerExtension]);

  function patch<K extends keyof MemorySettingsDTO>(
    key: K,
    value: Partial<MemorySettingsDTO[K]>,
  ) {
    if (!settings) return;
    setSettings({ ...settings, [key]: { ...settings[key], ...value } });
  }

  if (!settings) {
    return (
      <div
        style={{
          display: 'grid',
          placeItems: 'center',
          height: '60vh',
          fontSize: 13,
          color: 'rgba(0, 0, 0, 0.45)',
        }}
      >
        <Spin indicator={<LoadingOutlined spin />} />
      </div>
    );
  }

  return (
    <div data-tour="tour-memory">
      <SettingsPageHeader
        title="记忆"
        description="调整基于分块的 consolidator：每个模式 LLM 调用轮数、分块强度、引用校验严格程度。"
      />
      <SettingSection
        title="更新模式"
        description="增量抽取事实时默认的 LLM 轮数。工作台可单文档覆盖。"
      >
        <NumberRow
          label="L2 预算（每个 surface）"
          help="L2 更新时分块器最多产生的 chunk 数。"
          value={settings.update.l2_budget}
          onChange={(n) => patch('update', { l2_budget: n })}
          min={1}
          max={200}
        />
        <NumberRow
          label="L3 预算（每个 slot）"
          help="L3 更新时跨 7 个 L2 文档的最大 chunk 数。"
          value={settings.update.l3_budget}
          onChange={(n) => patch('update', { l3_budget: n })}
          min={1}
          max={200}
        />
      </SettingSection>

      <SettingSection
        title="检查模式"
        description="对照原始证据做行级编辑时的默认 LLM 轮数。"
      >
        <NumberRow
          label="L2 预算（每个 surface）"
          value={settings.audit.l2_budget}
          onChange={(n) => patch('audit', { l2_budget: n })}
          min={1}
          max={200}
        />
        <NumberRow
          label="L3 预算（每个 slot）"
          value={settings.audit.l3_budget}
          onChange={(n) => patch('audit', { l3_budget: n })}
          min={1}
          max={200}
        />
      </SettingSection>

      <SettingSection
        title="去重"
        description="对整个文档迭代去重。某轮无任何编辑时提前停止。"
      >
        <NumberRow
          label="迭代次数"
          value={settings.dedup.iterations}
          onChange={(n) => patch('dedup', { iterations: n })}
          min={1}
          max={20}
        />
        <ToggleRow
          label="更新后自动跑去重"
          value={settings.dedup.auto_after_update}
          onChange={(v) => patch('dedup', { auto_after_update: v })}
        />
      </SettingSection>

      <SettingSection
        title="合并脚注"
        description="无需 LLM 的整理：将重复的 ref 行合并为一个脚注后重新编号。幂等操作，任意时刻可安全运行。"
      >
        <ToggleRow
          label="Update 后自动合并"
          value={settings.merge.auto_after_update}
          onChange={(v) => patch('merge', { auto_after_update: v })}
        />
        <ToggleRow
          label="Audit 后自动合并"
          value={settings.merge.auto_after_audit}
          onChange={(v) => patch('merge', { auto_after_audit: v })}
        />
        <ToggleRow
          label="Dedup 后自动合并"
          value={settings.merge.auto_after_dedup}
          onChange={(v) => patch('merge', { auto_after_dedup: v })}
        />
      </SettingSection>

      <SettingSection
        title="分块"
        description="底层旋钮：控制内容如何切分。"
      >
        <NumberRow
          label="重叠比例"
          help="相邻 chunk 的字符重叠比例，0–0.5。"
          value={settings.chunking.overlap_ratio}
          onChange={(n) => patch('chunking', { overlap_ratio: n })}
          min={0}
          max={0.5}
          step={0.05}
          isFloat
        />
        <SelectRow
          label="切分边界"
          help="分块器倾向于在哪里切。"
          value={settings.chunking.boundary}
          options={[
            { value: 'paragraph', label: '段落' },
            { value: 'sentence', label: '句子' },
          ]}
          onChange={(v) =>
            patch('chunking', { boundary: v as 'paragraph' | 'sentence' })
          }
        />
        <NumberRow
          label="Chunk 最小字符数"
          help="单个 chunk 字符数下限。"
          value={settings.chunking.min_chunk_chars}
          onChange={(n) => patch('chunking', { min_chunk_chars: n })}
          min={200}
          max={64000}
          step={100}
        />
        <NumberRow
          label="Chunk 最大字符数"
          help="单个 chunk 字符数上限。"
          value={settings.chunking.max_chunk_chars}
          onChange={(n) => patch('chunking', { max_chunk_chars: n })}
          min={200}
          max={64000}
          step={100}
        />
      </SettingSection>

      <SettingSection
        title="引用"
        description="事实必须如何严格地引用其所在 chunk。"
      >
        <ToggleRow
          label="每条事实必须有 ref"
          help="丢弃没有 ref 的事实。"
          value={settings.reference.enforce_required}
          onChange={(v) => patch('reference', { enforce_required: v })}
        />
        <ToggleRow
          label="丢弃无效 ref（vs 拒绝整条事实）"
          help="开启：保留事实，只丢弃 chunk 范围之外的 ref。关闭：任何无效 ref 都会拒绝整条事实。"
          value={settings.reference.drop_invalid_refs}
          onChange={(v) => patch('reference', { drop_invalid_refs: v })}
        />
      </SettingSection>
    </div>
  );
}

// ── Field components ────────────────────────────────────────────────

interface NumberRowProps {
  label: string;
  help?: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
  step?: number;
  isFloat?: boolean;
}

function NumberRow({
  label,
  help,
  value,
  onChange,
  min,
  max,
  step = 1,
  isFloat = false,
}: NumberRowProps) {
  return (
    <SettingRow
      title={label}
      description={help}
      control={
        <InputNumber
          value={value}
          min={min}
          max={max}
          step={isFloat ? 0.05 : step}
          precision={isFloat ? 2 : undefined}
          onChange={(v) => {
            if (typeof v === 'number' && !Number.isNaN(v)) onChange(v);
          }}
          style={{ width: 96 }}
        />
      }
    />
  );
}

interface ToggleRowProps {
  label: string;
  help?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}

function ToggleRow({ label, help, value, onChange }: ToggleRowProps) {
  return (
    <SettingRow
      title={label}
      description={help}
      control={
        <Switch
          checked={value}
          onChange={onChange}
        />
      }
    />
  );
}

interface SelectRowProps {
  label: string;
  help?: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}

function SelectRow({ label, help, value, options, onChange }: SelectRowProps) {
  return (
    <SettingRow
      title={label}
      description={help}
      control={
        <div
          style={{
            display: 'flex',
            gap: 2,
            borderRadius: 8,
            background: 'rgba(0, 0, 0, 0.04)',
            padding: 2,
          }}
        >
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => onChange(o.value)}
              style={{
                borderRadius: 6,
                padding: '4px 10px',
                fontSize: 12,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
                ...(value === o.value
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
              {o.label}
            </button>
          ))}
        </div>
      }
    />
  );
}
