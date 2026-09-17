/**
 * 能力设置（1:1 复刻自原仓 web/app/(utility)/settings/capabilities/page.tsx）：
 * Chat / Solve / Question / Research / Math animator / Co-writer 六大区的
 * 每能力 LLM 参数与运行时旋钮（温度、max_tokens、轮次、预算、工具超时等）。
 * 保存走全局 Apply（registerExtension）；apiFetch/apiUrl → 相对路径 fetch；
 * NumberRow/ToggleRow → antd InputNumber / Switch。
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, InputNumber, Spin, Switch } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { useSettings } from '../../components/settings/SettingsContext';
import {
  SettingRow,
  SettingSection,
  SettingsPageHeader,
} from '../../components/settings/shared';

// ── Shape mirrors deeptutor/services/config/capabilities_settings.py ──────

interface SimpleLLMBlock {
  temperature: number;
  max_tokens: number;
}

interface ChatBlock {
  temperature: number;
  max_rounds: number;
  stage_budgets: {
    exploring: number;
    responding: number;
  };
}

interface ResearchExtras {
  researching: {
    note_agent_mode: string;
    tool_timeout: number;
    tool_max_retries: number;
    paper_search_years_limit: number;
  };
}

interface QuestionExtras {
  exploring: {
    max_iterations: number;
    tool_summarizer: {
      enabled: boolean;
      max_tokens: number;
    };
  };
}

interface SolveExtras {
  max_rounds: number;
  max_replans: number;
}

interface CapabilitiesSettingsDTO {
  chat: ChatBlock;
  solve: SimpleLLMBlock & SolveExtras;
  research: SimpleLLMBlock & ResearchExtras;
  question: SimpleLLMBlock & QuestionExtras;
  co_writer: SimpleLLMBlock;
  vision_solver: SimpleLLMBlock;
  math_animator: SimpleLLMBlock;
}

function isValidCapabilitiesDTO(
  value: unknown,
): value is CapabilitiesSettingsDTO {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  const chat = v.chat as Record<string, unknown> | undefined;
  const solve = v.solve as Record<string, unknown> | undefined;
  return (
    !!chat &&
    typeof chat.temperature === 'number' &&
    typeof chat.max_rounds === 'number' &&
    !!chat.stage_budgets &&
    !!solve &&
    typeof solve.max_rounds === 'number' &&
    typeof solve.max_replans === 'number' &&
    !!v.research &&
    !!v.question
  );
}

export default function CapabilitiesSettingsPage() {
  const { registerExtension } = useSettings();
  const [settings, setSettings] = useState<CapabilitiesSettingsDTO | null>(
    null,
  );
  const [serverSnapshot, setServerSnapshot] =
    useState<CapabilitiesSettingsDTO | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/capabilities/settings');
      if (!res.ok) {
        setLoadError(
          `加载能力设置失败 (HTTP ${res.status})。请确认后端已运行最新版本——/api/v1/capabilities/settings 接口是在本次发布中新增的。`,
        );
        return;
      }
      const data: unknown = await res.json();
      if (!isValidCapabilitiesDTO(data)) {
        setLoadError(
          '后端为 /api/v1/capabilities/settings 返回了意外的数据格式。请重启后端以加载最新 schema。',
        );
        return;
      }
      setSettings(data);
      setServerSnapshot(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : '加载能力设置失败。',
      );
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const dirty =
    !!settings &&
    !!serverSnapshot &&
    JSON.stringify(settings) !== JSON.stringify(serverSnapshot);

  const settingsRef = useRef(settings);
  useEffect(() => {
    settingsRef.current = settings;
  }, [settings]);
  const save = useCallback(async () => {
    const current = settingsRef.current;
    if (!current) return;
    const res = await fetch('/api/v1/capabilities/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(current),
    });
    if (!res.ok) {
      throw new Error(`保存能力设置失败（HTTP ${res.status}）`);
    }
    const data: unknown = await res.json();
    if (!isValidCapabilitiesDTO(data)) {
      throw new Error('保存后后端返回了意外的数据格式。');
    }
    setSettings(data);
    setServerSnapshot(data);
  }, []);

  useEffect(() => {
    registerExtension('capabilities', { dirty, save });
    return () => registerExtension('capabilities', null);
  }, [dirty, save, registerExtension]);

  function patchChat<K extends keyof ChatBlock>(key: K, value: ChatBlock[K]) {
    if (!settings) return;
    setSettings({ ...settings, chat: { ...settings.chat, [key]: value } });
  }

  function patchStageBudget(
    stage: keyof ChatBlock['stage_budgets'],
    value: number,
  ) {
    if (!settings) return;
    setSettings({
      ...settings,
      chat: {
        ...settings.chat,
        stage_budgets: { ...settings.chat.stage_budgets, [stage]: value },
      },
    });
  }

  function patchSimple(
    cap: 'solve' | 'co_writer' | 'vision_solver' | 'math_animator',
    value: Partial<SimpleLLMBlock>,
  ) {
    if (!settings) return;
    setSettings({ ...settings, [cap]: { ...settings[cap], ...value } });
  }

  function patchSolveExtras(value: Partial<SolveExtras>) {
    if (!settings) return;
    setSettings({ ...settings, solve: { ...settings.solve, ...value } });
  }

  function patchResearch(value: Partial<SimpleLLMBlock>) {
    if (!settings) return;
    setSettings({ ...settings, research: { ...settings.research, ...value } });
  }

  function patchResearching(value: Partial<ResearchExtras['researching']>) {
    if (!settings) return;
    setSettings({
      ...settings,
      research: {
        ...settings.research,
        researching: { ...settings.research.researching, ...value },
      },
    });
  }

  function patchQuestion(value: Partial<SimpleLLMBlock>) {
    if (!settings) return;
    setSettings({ ...settings, question: { ...settings.question, ...value } });
  }

  function patchExploring(value: Partial<QuestionExtras['exploring']>) {
    if (!settings) return;
    setSettings({
      ...settings,
      question: {
        ...settings.question,
        exploring: { ...settings.question.exploring, ...value },
      },
    });
  }

  function patchExploringSummarizer(
    value: Partial<QuestionExtras['exploring']['tool_summarizer']>,
  ) {
    if (!settings) return;
    setSettings({
      ...settings,
      question: {
        ...settings.question,
        exploring: {
          ...settings.question.exploring,
          tool_summarizer: {
            ...settings.question.exploring.tool_summarizer,
            ...value,
          },
        },
      },
    });
  }

  if (loadError) {
    return (
      <div
        style={{
          display: 'grid',
          placeItems: 'center',
          height: '60vh',
          padding: '0 24px',
        }}
      >
        <div
          style={{
            maxWidth: 576,
            borderRadius: 8,
            border: '1px solid #f0f0f0',
            background: '#fff',
            padding: 16,
            fontSize: 13,
            color: 'rgba(0, 0, 0, 0.45)',
          }}
        >
          <div style={{ marginBottom: 8, fontWeight: 500, color: 'rgba(0, 0, 0, 0.88)' }}>
            无法加载能力设置
          </div>
          <div>{loadError}</div>
          <Button
            onClick={() => void load()}
            style={{ marginTop: 12 }}
          >
            重试
          </Button>
        </div>
      </div>
    );
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
    <div data-tour="tour-capabilities">
      <SettingsPageHeader
        title="能力"
        description="各能力的 LLM 参数与运行时旋钮。"
      />

      <SettingSection
        title="聊天"
        description="探索 agent 循环后接 respond 阶段。各阶段预算限制每轮 LLM 的 max_tokens。"
      >
        <NumberRow
          label="温度"
          help="所有聊天阶段共享的采样温度。"
          value={settings.chat.temperature}
          onChange={(n) => patchChat('temperature', n)}
          min={0}
          max={2}
          step={0.05}
          isFloat
        />
        <NumberRow
          label="最大轮次"
          help="每轮探索循环 LLM 轮次的硬上限。无工具调用的一轮会提前结束循环。"
          value={settings.chat.max_rounds}
          onChange={(n) => patchChat('max_rounds', n)}
          min={1}
          max={50}
        />
        <NumberRow
          label="Exploring (max tokens)"
          help="Budget per exploring-loop round (notes + tool calls)."
          value={settings.chat.stage_budgets.exploring}
          onChange={(n) => patchStageBudget('exploring', n)}
          min={256}
          max={200000}
          step={100}
        />
        <NumberRow
          label="Responding (max tokens)"
          help="Budget for the final user-facing response."
          value={settings.chat.stage_budgets.responding}
          onChange={(n) => patchStageBudget('responding', n)}
          min={256}
          max={200000}
          step={100}
        />
      </SettingSection>

      <SettingSection
        title="解题"
        description="深度解题以单个 agent 循环运行，带有 计划 / 完成步骤 / 重新规划 的骨架。"
      >
        <NumberRow
          label="温度"
          value={settings.solve.temperature}
          onChange={(n) => patchSimple('solve', { temperature: n })}
          min={0}
          max={2}
          step={0.05}
          isFloat
        />
        <NumberRow
          label="最大 token 数"
          value={settings.solve.max_tokens}
          onChange={(n) => patchSimple('solve', { max_tokens: n })}
          min={256}
          max={200000}
          step={100}
        />
        <NumberRow
          label="最大轮次"
          help="单次解题的 LLM 总轮次预算（计划、工具调用、收尾都计入）。"
          value={settings.solve.max_rounds}
          onChange={(n) => patchSolveExtras({ max_rounds: n })}
          min={1}
          max={50}
        />
        <NumberRow
          label="最大重新规划次数"
          help="单轮内规划器可以修订计划的次数。"
          value={settings.solve.max_replans}
          onChange={(n) => patchSolveExtras({ max_replans: n })}
          min={0}
          max={10}
        />
      </SettingSection>

      <SettingSection
        title="题目"
        description="Deep Question（出题）生成流水线。"
      >
        <NumberRow
          label="温度"
          value={settings.question.temperature}
          onChange={(n) => patchQuestion({ temperature: n })}
          min={0}
          max={2}
          step={0.05}
          isFloat
        />
        <NumberRow
          label="最大 token 数"
          value={settings.question.max_tokens}
          onChange={(n) => patchQuestion({ max_tokens: n })}
          min={256}
          max={200000}
          step={100}
        />
        <NumberRow
          label="探索阶段最大迭代次数"
          help="规划前探索循环的上限。"
          value={settings.question.exploring.max_iterations}
          onChange={(n) => patchExploring({ max_iterations: n })}
          min={1}
          max={50}
        />
        <ToggleRow
          label="启用工具摘要器"
          help="对过长的工具输出进行摘要以控制 prompt 预算。"
          value={settings.question.exploring.tool_summarizer.enabled}
          onChange={(v) => patchExploringSummarizer({ enabled: v })}
        />
        <NumberRow
          label="工具摘要器（最大 token 数）"
          value={settings.question.exploring.tool_summarizer.max_tokens}
          onChange={(n) => patchExploringSummarizer({ max_tokens: n })}
          min={128}
          max={200000}
          step={100}
        />
      </SettingSection>

      <SettingSection
        title="研究"
        description="Deep Research 流水线。迭代次数按请求由聊天输入框中的深度选择器（快速 / 标准 / 深度 / 手动）控制，不在此处设置。"
      >
        <NumberRow
          label="温度"
          value={settings.research.temperature}
          onChange={(n) => patchResearch({ temperature: n })}
          min={0}
          max={2}
          step={0.05}
          isFloat
        />
        <NumberRow
          label="最大 token 数"
          value={settings.research.max_tokens}
          onChange={(n) => patchResearch({ max_tokens: n })}
          min={256}
          max={200000}
          step={100}
        />
        <NumberRow
          label="工具超时（秒）"
          help="研究阶段每个工具的实际耗时超时上限。"
          value={settings.research.researching.tool_timeout}
          onChange={(n) => patchResearching({ tool_timeout: n })}
          min={1}
          max={600}
        />
        <NumberRow
          label="工具最大重试次数"
          value={settings.research.researching.tool_max_retries}
          onChange={(n) => patchResearching({ tool_max_retries: n })}
          min={0}
          max={10}
        />
        <NumberRow
          label="论文搜索年限"
          help="论文搜索回溯多少年。"
          value={settings.research.researching.paper_search_years_limit}
          onChange={(n) => patchResearching({ paper_search_years_limit: n })}
          min={1}
          max={50}
        />
      </SettingSection>

      <SettingSection
        title="数学动画"
        description="Manim 动画 / 图像生成流水线。"
      >
        <NumberRow
          label="温度"
          value={settings.math_animator.temperature}
          onChange={(n) => patchSimple('math_animator', { temperature: n })}
          min={0}
          max={2}
          step={0.05}
          isFloat
        />
        <NumberRow
          label="最大 token 数"
          value={settings.math_animator.max_tokens}
          onChange={(n) => patchSimple('math_animator', { max_tokens: n })}
          min={256}
          max={200000}
          step={100}
        />
      </SettingSection>

      <SettingSection
        title="Co-writer"
        description="选区编辑 / 行内改写 Agent。"
      >
        <NumberRow
          label="温度"
          value={settings.co_writer.temperature}
          onChange={(n) => patchSimple('co_writer', { temperature: n })}
          min={0}
          max={2}
          step={0.05}
          isFloat
        />
        <NumberRow
          label="最大 token 数"
          value={settings.co_writer.max_tokens}
          onChange={(n) => patchSimple('co_writer', { max_tokens: n })}
          min={256}
          max={200000}
          step={100}
        />
      </SettingSection>
    </div>
  );
}

// ── Field components (mirrors memory page) ─────────────────────────────

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
          style={{ width: 112 }}
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
