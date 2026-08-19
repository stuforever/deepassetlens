/**
 * 受控 Skill 问答平台 v2 - 前端契约卡片类型
 * 页面展示与后端 QueryContract 完全一致（不允许前端自行猜测）。
 */

export type RouteResult = {
  route_type: string; // scenario | clarification | generic | fallback | reject
  skill_id?: string;
  workflow_step?: string;
  matched_rules?: string[];
  route_reason?: string;
  confidence?: string;
  fallback_level?: string;
  candidates?: Array<{ skill_id: string; description?: string }>;
  priority?: number;
  contract?: Record<string, any> | null;
};

export type QueryContractView = {
  run_id?: string;
  skill_id: string;
  skill_version?: string;
  workflow_step: string;
  allowed_tools?: string[];
  forbidden_tools?: string[];
  template_ids?: string[];
  scope?: Record<string, any>;
  selected_engine?: string | null;
  engine_reason?: string | null;
  output_mode?: string;
  multi_engine?: boolean;                    // 批4：多数据源逐源分发（引擎不唯一）
  forbid_markdown_detail_table?: boolean;    // 批4：答案不得再画 Markdown 明细表
  confirmed_engines?: string[];              // 批4/评审P1-4：后端真实确认引擎集合
  entity_engine_map?: Record<string, string>;// 批4/评审P1-4：实体 -> 引擎 真实映射
  stop_reached?: boolean;                    // 评审P1-2：多引擎两源取齐即终止
  required_entities?: string[];              // 评审P1-1：必达数据源（SKILL required_sources 声明）
  confirmed_entities?: string[];             // 评审P1-1：已确认 source_mode 的实体
  completed_entities?: string[];             // 评审P1-1：已取到结果的实体（终止判定依据）
  stop_when?: string[];
  route_reason?: string;
  route_type?: string;
};

// 评审 P2-2（二轮）：策略事件（policy.rejected 等）与模板事件（template.bound/drift）视图
export type PolicyEventView = {
  run_id?: string;
  tool_call_id?: string;
  kind?: string;
  reason?: string;
  detail?: string;
};

export type TemplateEventView = {
  run_id?: string;
  tool_call_id?: string;
  kind?: 'template.bound' | 'template.drift' | string;
  detail?: string;
  structure_match?: boolean;
  template_id?: string;
};

export const ROUTE_TYPE_META: Record<string, { label: string; color: string }> = {
  scenario: { label: '精确场景剧本', color: 'green' },
  clarification: { label: '需用户澄清', color: 'orange' },
  generic: { label: '低权限只读通用', color: 'blue' },
  fallback: { label: '只读降级', color: 'blue' },
  reject: { label: '拒绝执行', color: 'red' },
};

export const ENGINE_META: Record<string, { label: string; color: string }> = {
  doris: { label: 'Doris 联邦', color: 'purple' },
  duckdb: { label: 'DuckDB API 联邦', color: 'cyan' },
  physical: { label: '物理表直连', color: 'geekblue' },
};

export const SKILL_CN: Record<string, string> = {
  'distribution-overload': '配电变压器重过载分析',
  '__generic__': '通用受限查询',
};

// touch
