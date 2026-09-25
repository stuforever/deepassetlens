import { v1Api as api } from './http';
import { createApiClient } from './http';
import type { AxiosRequestConfig } from 'axios';
import type { DataSourceInput } from './types';

const API_BASE_URL = '/api/v1';
// 数据引擎观测（批3）：独立 /api/engine 实例（与 /api/v1 不同前缀）
const engineClient = createApiClient('/api/engine');

export const conceptApi = {
  getConcepts: (level?: number, includeLevel0 = false) => api.get('/concepts', { params: { level, include_level_zero: includeLevel0 } }),
  createConcept: (data: any) => api.post('/concepts', data),
  updateConcept: (id: string, data: any) => api.put(`/concepts/${id}`, data),
  deleteConcept: (id: string) => api.delete(`/concepts/${id}`),
  clearGraphData: (mode?: string) => api.post('/concepts/clear', null, { params: { mode } }),
  syncToNeo4j: () => api.post('/sync'),
  getGraphData: () => api.get('/graph/data'),
  getNeo4jGraphData: () => api.get('/graph/neo4j-data'),
  getGraphMatrix: () => api.get('/graph/matrix'),
  getSubgraphByL1: (l1Id: string) => api.get(`/graph/subgraph-by-l1/${l1Id}`),
  exportExcel: (mode?: string) => `${API_BASE_URL}/export/excel${mode ? `?mode=${mode}` : ''}`,
  importExcel: (formData: FormData, mode?: string, clear = false) => api.post('/import/excel', formData, {
    params: { mode, clear },
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

export const entityApi = {
  listEntities: () => api.get('/entities'),
  createEntity: (data: any) => api.post('/entities', data),
  updateEntity: (id: string, data: any) => api.put(`/entities/${id}`, data),
  deleteEntity: (id: string) => api.delete(`/entities/${id}`),
  suggestEntityExplanations: (data: any) => api.post('/entities/explanation-suggestions', data),
  checkEntityEnNameIntegrity: () => api.get('/entities/en-name-integrity-check'),
  autoFillEntityEnName: (only_empty = true) => api.post('/entities/en-name-autofill', { only_empty }),
  toggleMatrixLink: (entityId: string, targetEntityId: string) => 
    api.post(`/entities/${entityId}/matrix/toggle`, null, { params: { target_entity_id: targetEntityId } }),
};

export const entityRelationApi = {
  getRelations: (entityId?: string) => api.get('/entity-relations', { params: { entity_id: entityId } }),
  createRelation: (data: any) => api.post('/entity-relations', data),
  updateRelation: (id: string, data: any) => api.put(`/entity-relations/${id}`, data),
  deleteRelation: (id: string) => api.delete(`/entity-relations/${id}`),
};

export const entityRelationManagerApi = {
  listItems: (params?: any) => api.get('/entity-relation-manager/items', { params }),
  createItem: (data: any) => api.post('/entity-relation-manager/items', data),
  updateItem: (id: string, data: any) => api.put(`/entity-relation-manager/items/${id}`, data),
  deleteItem: (id: string) => api.delete(`/entity-relation-manager/items/${id}`),
  exportExcel: (params?: Record<string, any>) => {
    const query = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, String(value));
      }
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return `${API_BASE_URL}/entity-relation-manager/export/excel${suffix}`;
  },
  importExcel: (formData: FormData) => api.post('/entity-relation-manager/import/excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

export const mappingApi = {
  getSources: () => api.get('/sources'),
  registerSource: (data: any) => api.post('/sources', data),
  getMappings: (entityId: string) => api.get(`/mappings/${entityId}`),
  createMapping: (data: any) => api.post('/mappings', data),
  getLineage: (entityId: string) => api.get(`/lineage/${entityId}`),
  createMappingRule: (data: any) => api.post('/rules', data),
  getMappingRules: (entityId?: string) => api.get('/rules', { params: entityId ? { entity_id: entityId } : {} }),
  getMappingRuleDetail: (id: string) => api.get(`/rules/${id}`),
  updateMappingRule: (id: string, data: any) => api.put(`/rules/${id}`, data),
  deleteMappingRule: (id: string) => api.delete(`/rules/${id}`),
  previewEntityData: (entityId: string, limit = 20) => api.get(`/entity-preview/${entityId}?limit=${limit}`),
};

export const chatApi = {
  ask: (query: string) => api.post('/chat', { query }),
};

export const smartAppApi = {
  recommendJoin: (data: { intent: string; entity_id?: string; top_k?: number }) =>
    api.post('/smart-apps/join/recommend', data),
  reviewAndExecuteJoin: (data: {
    intent: string;
    candidate_id: string;
    sql_text: string;
    confidence: number;
    need_manual_review: boolean;
    approved: boolean;
    reviewer?: string;
    execute_after_approve?: boolean;
    limit?: number;
    candidate_payload?: any;
  }) => api.post('/smart-apps/join/review-and-execute', data),
  getJoinReviews: (limit = 20) => api.get(`/smart-apps/join/reviews?limit=${limit}`),
};

export const standardSemanticApi = {
  getModelConfig: () => api.get('/standard-semantics/model-config'),
  getVectorModels: () => api.get('/standard-semantics/vector-models'),
  updateModelConfig: (data: any) => api.put('/standard-semantics/model-config', data),
  extractFromGraph: (reset_existing = false, extract_mode = 'all') => 
    api.post('/standard-semantics/extract-from-graph', { reset_existing, extract_mode }),
  listTerms: (params?: { term_type?: string; keyword?: string; vector_status?: string; entity_scope?: 'data' | 'concept' | 'all'; limit?: number }) =>
    api.get('/standard-semantics/terms', { params }),
  vectorize: (data: {
    term_ids?: string[];
    force_regenerate?: boolean;
    normalize_l2?: boolean;
    max_retries?: number;
    batch_size?: number;
    model_name?: string;
  }) => api.post('/standard-semantics/vectorize', data),
  listVectorTasks: (limit = 20) => api.get('/standard-semantics/vector-tasks', { params: { limit } }),
  queryVectors: (data: {
    query_text: string;
    top_k?: number;
    term_types?: string[];
    normalize_l2?: boolean;
    bind_ontology?: boolean;
    entity_scope?: 'data' | 'concept' | 'all';
  }) => api.post('/standard-semantics/query', data),
  exportVectors: (data: { format: 'json' | 'parquet' | 'vector_store'; include_ontology_bind?: boolean; term_types?: string[]; entity_scope?: 'data' | 'concept' | 'all' }) =>
    api.post('/standard-semantics/export', data),
};

// ---- 向量管理（对接系统A：entity_embeddings + attribute_embeddings 双库）----
// 智能问答的 locate_entity_attribute / explore 技能通过 skill_injections 读取这两个库
// 模型列表/当前模型复用 standardSemanticApi.getVectorModels / getModelConfig
export const vectorManageApi = {
  // 双库统计
  getEntityVectorStats: () => api.get('/sync/entity-vector-stats'),
  getAttributeVectorStats: () => api.get('/sync/attribute-vector-stats'),
  // 单库同步（force=true 全量重建 / force=false 增量同步）
  syncEntityVectors: (force: boolean = false) =>
    api.post(`/sync/entity-vectors?force=${force}`),
  syncAttributeVectors: (force: boolean = false) =>
    api.post(`/sync/attribute-vectors?force=${force}`),
  // 查询测试（下拉选择库，分开查）
  queryVectors: (data: { collection: 'entity' | 'attribute'; query: string; top_k?: number }) =>
    api.post('/sync/query-vectors', data),
};

// ---- 自定义知识库（RAG：上传文档 -> 向量化 -> 检索增强）----
export const knowledgeBaseApi = {
  list: () => api.get('/knowledge-bases'),
  get: (id: string) => api.get(`/knowledge-bases/${id}`),
  create: (data: { name: string; description?: string; type?: string; rag_provider?: string; pointer_params?: Record<string, unknown> }) => api.post('/knowledge-bases', data),
  delete: (id: string) => api.delete(`/knowledge-bases/${id}`),
  upload: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/knowledge-bases/${id}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  vectorize: (id: string) => api.post(`/knowledge-bases/${id}/vectorize`),
  deleteDoc: (id: string, docId: string) => api.delete(`/knowledge-bases/${id}/documents/${docId}`),
  search: (id: string, query: string, top_k = 5) =>
    api.post(`/knowledge-bases/${id}/search`, { query, top_k }),
  // ④批4：增量对账+手动重嵌（spec D8——重嵌永远手动）
  reconcile: (id: string) => api.post(`/knowledge-bases/${id}/reconcile`),
  reembed: (id: string) => api.post(`/knowledge-bases/${id}/reembed`),
};

export const smartSkillApi = {
  // 技能管理 API
  getSkills: (appType?: string) => api.get('/smart-skills', { params: { app_type: appType } }),
  bootstrapSmartJoinSkillset: () => api.post('/smart-skills/bootstrap-smart-join'),
  bootstrapSmartJoinSixstep: () => api.post('/smart-skills/bootstrap-smart-join-sixstep'),
  bootstrapSmartQaSixstep: () => api.post('/smart-skills/bootstrap-smart-qa-sixstep'),
  bootstrapStep1MicroSkills: () => api.post('/smart-skills/bootstrap-step1-micro-skills'),
  createSkill: (data: any) => api.post('/smart-skills', data),
  updateSkill: (id: string, data: any) => api.put(`/smart-skills/${id}`, data),
  deleteSkill: (id: string) => api.delete(`/smart-skills/${id}`),
  testSkill: (id: string, input_payload: any) => api.post(`/smart-skills/${id}/test`, { input_payload }),
  scriptAssistant: (
    id: string,
    data: {
      task_type: 'generate' | 'fix' | 'explain';
      requirement?: string;
      error_message?: string;
      input_sample?: any;
      output_expectation?: any;
      auto_apply?: boolean;
    }
  ) => api.post(`/smart-skills/${id}/script-assistant`, data),
  
  // 新增API端点
  saveDraft: (id: string, data: any) => api.post(`/smart-skills/${id}/save-draft`, data),
  publishSkill: (id: string) => api.post(`/smart-skills/${id}/publish`),

  // 类型管理 API
  getSkillTypes: (includeDisabled?: boolean) => api.get('/skill-types', { params: { include_disabled: includeDisabled } }),
  createSkillType: (data: any) => api.post('/skill-types', data),
  updateSkillType: (id: string, data: any) => api.put(`/skill-types/${id}`, data),
  deleteSkillType: (id: string) => api.delete(`/skill-types/${id}`),
  bootstrapSkillTypes: () => api.post('/skill-types/bootstrap'),

  // 工作流管理 API
  getWorkflows: (appType?: string, targetMenu?: string) =>
    api.get('/smart-skill-workflows', { params: { app_type: appType, target_menu: targetMenu } }),
  createWorkflow: (data: any) => api.post('/smart-skill-workflows', data),
  updateWorkflow: (id: string, data: any) => api.put(`/smart-skill-workflows/${id}`, data),
  deleteWorkflow: (id: string) => api.delete(`/smart-skill-workflows/${id}`),
  runWorkflow: (id: string, input_payload: any) => api.post(`/smart-skill-workflows/${id}/run`, { input_payload }),
  getWorkflowRuns: (id: string, limit = 20) => api.get(`/smart-skill-workflows/${id}/runs?limit=${limit}`),
  getSemanticStatus: () => api.get('/smart-skills/semantic/status'),
  rebuildSemanticIndex: (force_rebuild = true) => api.post('/smart-skills/semantic/rebuild-index', { force_rebuild }),
};

export const metricCenterApi = {
  listMetrics: (params?: { domain?: string; status?: string; metric_type?: string; keyword?: string }) => api.get('/metrics', { params }),
  getMetric: (id: string) => api.get(`/metrics/${id}`),
  createMetric: (data: any) => api.post('/metrics', data),
  updateMetric: (id: string, data: any) => api.put(`/metrics/${id}`, data),
  deleteMetric: (id: string) => api.delete(`/metrics/${id}`),

  upsertAliases: (id: string, aliases: any[]) => api.put(`/metrics/${id}/aliases`, { aliases }),
  upsertAtom: (id: string, atom: any) => api.put(`/metrics/${id}/atom`, atom),
  upsertAtomFilters: (id: string, filters: any[]) => api.put(`/metrics/${id}/atom-filters`, { filters }),
  upsertDerived: (id: string, derived: any) => api.put(`/metrics/${id}/derived`, derived),
  upsertDeps: (id: string, deps: any[]) => api.put(`/metrics/${id}/deps`, { deps }),
  upsertDimBindings: (id: string, bindings: any[]) => api.put(`/metrics/${id}/dim-bindings`, { bindings }),
  upsertFilterWhitelist: (id: string, fields: any[]) => api.put(`/metrics/${id}/filter-whitelist`, { fields }),

  listVersions: (id: string) => api.get(`/metrics/${id}/versions`),
  getVersionSnapshot: (id: string, version: number) => api.get(`/metrics/${id}/versions/${version}`),
  listAuditLogs: (id: string) => api.get(`/metrics/${id}/audit-logs`),
  getLineage: (id: string, depth = 2) => api.get(`/metrics/${id}/lineage`, { params: { depth } }),

  submit: (id: string, data: { operator?: string; reason?: string }) => api.post(`/metrics/${id}/submit`, data),
  approve: (id: string, data: { operator?: string; reason?: string }) => api.post(`/metrics/${id}/approve`, data),
  reject: (id: string, data: { operator?: string; reason?: string }) => api.post(`/metrics/${id}/reject`, data),
  publish: (id: string, data: { operator?: string; reason?: string }) => api.post(`/metrics/${id}/publish`, data),
  rollback: (id: string, data: { version: number; operator?: string; reason?: string }) => api.post(`/metrics/${id}/rollback`, data),
};

export const llmAdminApi = {
  getConnections: () => api.get('/llm-connections'),
  createConnection: (data: any) => api.post('/llm-connections', data),
  updateConnection: (id: string, data: any) => api.put(`/llm-connections/${id}`, data),
  duplicateConnection: (id: string) => api.post(`/llm-connections/${id}/duplicate`),
  deleteConnection: (id: string) => api.delete(`/llm-connections/${id}`),
  testConnection: (id: string) => api.post(`/llm-connections/${id}/test`),
  updateCapabilities: (id: string, capabilities: Record<string, boolean>) =>
    api.put(`/llm-connections/${id}/capabilities`, { capabilities }),   // ③模型目录化：实测回填
  chatByConnection: (
    id: string,
    data: { messages?: Array<{ role: string; content: string }>; user_input?: string; system_prompt?: string; temperature?: number; max_tokens?: number }
  ) => api.post(`/llm-connections/${id}/chat`, data),
  getPlannerConfig: () => api.get('/planner-config'),
  upsertPlannerConfig: (data: any) => api.put('/planner-config', data),
};

export const queryEntityApi = {
  getExampleMetadata: () => api.get('/query-entity/example-metadata'),
  getSystemMetadata: () => api.get('/query-entity/system-metadata'),
  mapQuery: (data: {
    user_query: string;
    metadata_source?: 'system' | 'manual';
    metadata?: any;
    llm_connection_id?: string;
    enable_llm_disambiguation?: boolean;
  }) => api.post('/query-entity/map', data),
};

export const runApi = {
  createConversation: (data: {
    scene_code?: string;
    page_code?: string;
    title?: string;
    metadata?: any;
  }) => api.post('/conversations', data),
  getConversation: (id: string) => api.get(`/conversations/${id}`),
  getConversationMessages: (id: string) => api.get(`/conversations/${id}/messages`),
  createRun: (data: {
    conversation_id?: string;
    scene_code?: string;
    page_code?: string;
    message: string;
    async_mode?: boolean;
    input_payload?: any;
    target_code?: string;
  }) => api.post('/runs', data),
  getRun: (id: string) => api.get(`/runs/${id}`),
  getRunByCode: (runCode: string) => api.get(`/runs/by-code/${runCode}`),
  getRunEvents: (id: string, sinceOrder = 0) => api.get(`/runs/${id}/events`, { params: { since_order: sinceOrder } }),
  getRunEventsStreamUrl: (id: string, sinceOrder = 0) => `${API_BASE_URL}/runs/${id}/events/stream?since_order=${sinceOrder}`,
  getRunEventsStreamText: async (id: string, sinceOrder = 0) => {
    const resp = await fetch(`${API_BASE_URL}/runs/${id}/events/stream?since_order=${sinceOrder}`);
    if (!resp.ok) {
      throw new Error(`读取事件流失败: ${resp.status}`);
    }
    return resp.text();
  },
};

export const uploadApi = {
  uploadSourceFields: (formData: FormData) => api.post('/source_fields/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getSourceTableFields: (sysCode: string, tableEn: string) =>
    api.get(`/source_tables/${encodeURIComponent(sysCode || '')}/${encodeURIComponent(tableEn || '')}/fields`),
};

export const sourceFieldApi = {
  getAllFields: () => api.get('/source_fields'),
  createField: (data: any) => api.post('/source_fields', data),
  updateField: (id: string, data: any) => api.put(`/source_fields/${id}`, data),
  deleteField: (id: string) => api.delete(`/source_fields/${id}`),
};

export const sourceTableApi = {
  getAllTables: () => api.get('/source_tables/all'),
  bulkSaveTables: (data: { master_data: any[], business_data: any[], reference_data: any[] }) => api.post('/source_tables/bulk_save', data),
  getAllRelations: () => api.get('/source_tables/relations/all'),
  bulkSaveRelations: (data: { l2_relations: any[], l4_relations: any[], cross_relations: any[] }) => api.post('/source_tables/relations/bulk_save', data),
};

export const kgApi = {
  executeSql: (sql: string) => api.post('/api/kg/execute_sql', { sql }),
  entitySourceMode: (entityCode: string) => api.get(`/api/kg/entity_source_mode/${entityCode}`),
};

// 多源API映射（DuckDB联邦查询，配置驱动）
export const apiEndpointApi = {
  list: (entityId?: string) => api.get('/api-endpoints', { params: entityId ? { entity_id: entityId } : {} }),
  create: (data: any) => api.post('/api-endpoints', data),
  get: (id: string) => api.get(`/api-endpoints/${id}`),
  update: (id: string, data: any) => api.put(`/api-endpoints/${id}`, data),
  delete: (id: string) => api.delete(`/api-endpoints/${id}`),
  test: (id: string) => api.post(`/api-endpoints/${id}/test`, {}),
  execute: (sql: string) => api.post('/api-endpoints/execute', { sql }),
  tables: () => api.get('/api-endpoints/tables'),
};

// integration_sql 执行（sql_integration 模式，Doris 引擎）
export const integrationSqlApi = {
  verify: (sql: string, catalog?: string) => api.post('/integration-sql/verify', { sql, catalog }),
  aiRewrite: (sql: string, entityId: string, catalog?: string, connectionId?: string) => api.post('/integration-sql/ai-rewrite', { sql, entity_id: entityId, catalog, connection_id: connectionId }),
  execute: (entityCode: string, filters?: Record<string, any>) => api.post('/integration-sql/execute', { entity_code: entityCode, filters }),
};

// Doris 配置 + Catalog 管理（sql_integration 引擎配置）
export const dorisApi = {
  getConfig: (config?: AxiosRequestConfig) => api.get('/doris/config', config),
  putConfig: (cfg: Record<string, any>, config?: AxiosRequestConfig) => api.put('/doris/config', cfg, config),
  testConnection: (cfg?: Record<string, any>, config?: AxiosRequestConfig) => api.post('/doris/config/test', cfg || {}, config),
  listCatalogs: (config?: AxiosRequestConfig) => api.get('/doris/catalogs', config),
  createCatalog: (c: Record<string, any>, config?: AxiosRequestConfig) => api.post('/doris/catalogs', c, config),
  deleteCatalog: (name: string, config?: AxiosRequestConfig) => api.delete(`/doris/catalogs/${encodeURIComponent(name)}`, config),
  // P4：es/jdbc catalog 探活 + 刷新元数据
  probeCatalog: (name: string, config?: AxiosRequestConfig) => api.post(`/doris/catalogs/${encodeURIComponent(name)}/probe`, {}, config),
  refreshCatalog: (name: string, config?: AxiosRequestConfig) => api.post(`/doris/catalogs/${encodeURIComponent(name)}/refresh`, {}, config),
};

// 对象API映射（对象层面整合多源API，伪逻辑SQL+字段映射）
export const entityApiMappingApi = {
  list: (entityId?: string) => api.get('/entity-api-mappings', { params: entityId ? { entity_id: entityId } : {} }),
  create: (data: any) => api.post('/entity-api-mappings', data),
  get: (id: string) => api.get(`/entity-api-mappings/${id}`),
  update: (id: string, data: any) => api.put(`/entity-api-mappings/${id}`, data),
  delete: (id: string) => api.delete(`/entity-api-mappings/${id}`),
  verify: (id: string) => api.post(`/entity-api-mappings/${id}/verify`),
  execute: (entityCode: string, filters?: Record<string, any>) => api.post('/entity-api-mappings/execute', { entity_code: entityCode, filters }),
};

// 数据源配置（DataSourceConfig 页 + ModelTreeManager physical_table 绑定用）
// config.silent=true 时由调用方自行展示错误（保持其原有精细报错，避免与统一层双弹）。
export const dataSourceApi = {
  list: (config?: AxiosRequestConfig) => api.get('/data-sources', config),
  get: (id: string, config?: AxiosRequestConfig) => api.get(`/data-sources/${id}`, config),
  create: (data: DataSourceInput, config?: AxiosRequestConfig) => api.post('/data-sources', data, config),
  update: (id: string, data: Partial<DataSourceInput>, config?: AxiosRequestConfig) => api.put(`/data-sources/${id}`, data, config),
  remove: (id: string, config?: AxiosRequestConfig) => api.delete(`/data-sources/${id}`, config),
  test: (id: string, config?: AxiosRequestConfig) => api.post(`/data-sources/${id}/test`, {}, config),
};

// 资源级 ACL（ResourceAclDrawer）
export const aclApi = {
  getGrants: (resourceType: string, resourceId: string, config?: AxiosRequestConfig) =>
    api.get('/auth/grants', { params: { resource_type: resourceType, resource_id: resourceId }, ...config }),
  listUsers: (config?: AxiosRequestConfig) => api.get('/auth/users', config),
  grant: (data: { resource_type: string; resource_id: string; principal_type: string; principal_id: string; actions: string[]; expires_at?: string }, config?: AxiosRequestConfig) =>
    api.post('/auth/grant', data, config),
  revoke: (id: number, config?: AxiosRequestConfig) => api.delete(`/auth/grant/${id}`, config),
};

// 数据引擎观测（批3：健康/缓存/查询日志/EXPLAIN；P3/P4/P5 深化）
export const engineApi = {
  health: (config?: AxiosRequestConfig) => engineClient.get('/health', config),
  cacheStats: (config?: AxiosRequestConfig) => engineClient.get('/cache/stats', config),
  cacheInvalidate: (endpointId?: string, config?: AxiosRequestConfig) =>
    engineClient.post('/cache/invalidate', { endpoint_id: endpointId || null }, config),
  queries: (params?: { limit?: number; offset?: number; engine?: string; status?: string }, config?: AxiosRequestConfig) =>
    engineClient.get('/queries', { params, ...config }),
  explain: (sql: string, catalog?: string, verbose?: boolean, config?: AxiosRequestConfig) =>
    engineClient.post('/explain', { sql, catalog, verbose: !!verbose }, config),
  // P3：熔断/限速状态
  circuits: (config?: AxiosRequestConfig) => engineClient.get('/circuits', config),
  // P3/P5：Pushdown 调试器（解析+下推树，不真实执行）
  pushdownDebug: (sql: string, config?: AxiosRequestConfig) =>
    engineClient.post('/pushdown/debug', { sql }, config),
  // P4：Profile 代理（FE 18030 查询画像）
  profile: (queryId: string, config?: AxiosRequestConfig) =>
    engineClient.get('/profile', { params: { query_id: queryId }, ...config }),
  // P5：预聚合加速器
  accelerators: (config?: AxiosRequestConfig) => engineClient.get('/accelerators', config),
  acceleratorCreate: (data: Record<string, unknown>, config?: AxiosRequestConfig) =>
    engineClient.post('/accelerators', data, config),
  acceleratorUpdate: (id: string, data: Record<string, unknown>, config?: AxiosRequestConfig) =>
    engineClient.put(`/accelerators/${id}`, data, config),
  acceleratorDelete: (id: string, config?: AxiosRequestConfig) =>
    engineClient.delete(`/accelerators/${id}`, config),
  acceleratorRefresh: (id: string, config?: AxiosRequestConfig) =>
    engineClient.post(`/accelerators/${id}/refresh`, {}, config),
  acceleratorRefreshAll: (config?: AxiosRequestConfig) =>
    engineClient.post('/accelerators/refresh/all', {}, config),
};

// ===== 金标锚定管理（批13-C 题库移除：示例库 -> 金标，/api/v1/golden-qa）=====

// ===== 金标锚定管理（批13-C 题库移除：示例库 -> 金标，/api/v1/golden-qa）=====
export type GoldenQaItem = {
  id: string;
  question: string;
  expected_sql?: string | null;
  expected_result_digest?: { row_count?: number; first_row_hash?: string } | null;
  route_type?: string;
  scenario_tag?: string | null;
  enabled?: boolean;
  engine?: string | null;      // doris | physical | duckdb | api_integration
  hit_count?: number;          // 批13-C：命中统计
  last_hit_at?: string | null; // 最近命中时间
  created_at?: string | null;
};

export type GoldenCandidate = {
  question: string;        // 展示串（最近一次反馈原文）
  up_count: number;
  down_count: number;
  total: number;
  last_seen?: string | null;
  latest_sql?: string;     // 反馈 SQL 存证（corrected 优先）
};

export const goldenQaApi = {
  list: (params?: { enabled_only?: boolean }, config?: AxiosRequestConfig) =>
    api.get('/golden-qa', { params, ...config }),
  create: (data: { question: string; expected_sql: string; expected_result_digest?: object; route_type?: string; scenario_tag?: string; engine?: string }, config?: AxiosRequestConfig) =>
    api.post('/golden-qa', data, config),
  seed: (config?: AxiosRequestConfig) => api.post('/golden-qa/seed', {}, config),
  reseedVectors: (config?: AxiosRequestConfig) => api.post('/golden-qa/reseed', {}, config),
  candidates: (params?: { days?: number; top_m?: number }, config?: AxiosRequestConfig) =>
    api.get('/golden-qa/candidates', { params, ...config }),
  setStatus: (id: string, enabled: boolean, config?: AxiosRequestConfig) =>
    api.patch(`/golden-qa/${id}`, { enabled }, config),
  remove: (id: string, config?: AxiosRequestConfig) =>
    api.delete(`/golden-qa/${id}`, config),
};

// ===== 安全控制中心（《安全控制中心实施设计》，/api/guards）=====
// guards 路由自带 /api 前缀（不经 /api/v1），独立 client
const guardsClient = createApiClient('/api');

export interface GuardDescription {
  what: string;
  lose: string;
  remain: string;
}

export interface GuardStats {
  h24: number;
  h7d: number;
  last_block_at?: string | null;
}

export interface GuardItem {
  guard_id: string;
  title: string;
  enabled: boolean;
  mode: string;                              // block | warn | log
  params: Record<string, unknown>;
  risk_level: 'red' | 'yellow' | 'green';
  description: GuardDescription;
  confirm_required: boolean;
  stats?: GuardStats;
  updated_by?: string | null;
  updated_at?: string | null;
  close_reason?: string | null;
  version: number;
}

export interface GuardEventItem {
  id: number;
  guard_id: string;
  ts?: string | null;
  action: string;                            // block|warn|pass|probe|toggle|reset
  question_digest?: string | null;
  verdict?: string | null;
  detail?: Record<string, unknown>;
  updated_by?: string | null;
}

export const guardsApi = {
  list: (config?: AxiosRequestConfig) => guardsClient.get('/guards', config),
  update: (guardId: string, body: { enabled?: boolean; mode?: string; params?: Record<string, unknown>; confirm?: boolean; close_reason?: string }, config?: AxiosRequestConfig) =>
    guardsClient.patch(`/guards/${guardId}`, body, config),
  probe: (guardId: string, config?: AxiosRequestConfig) =>
    guardsClient.post(`/guards/${guardId}/probe`, {}, config),
  events: (params?: { guard_id?: string; range?: string; page?: number; page_size?: number }, config?: AxiosRequestConfig) =>
    guardsClient.get('/guards/events', { params, ...config }),
  resetDefaults: (config?: AxiosRequestConfig) =>
    guardsClient.post('/guards/reset-defaults', {}, config),
  preset: (mode: 'turbo' | 'safe', config?: AxiosRequestConfig) =>
    guardsClient.post('/guards/preset', { mode }, config),
};

// ===== 能力开关中心（批13-Q，/api/capabilities）=====
export interface SubagentSpec {
  name: string;
  description: string;
  prompt: string;
  tools: string[];
}

export interface CapabilityStats {
  probe_pass_rate?: number | null;
  probe_total_7d?: number;
  task_invoke_7d?: number;
  last_change?: string | null;
}

export interface CapabilityItem {
  capability_id: string;
  title: string;
  enabled: boolean;
  params: Record<string, unknown>;
  risk_level: 'red' | 'yellow' | 'green';
  description: { what?: string; lose?: string; remain?: string };
  confirm_required: boolean;
  physical_blocked: boolean;
  blocked_reason?: string | null;
  stats?: CapabilityStats;
  updated_by?: string | null;
  updated_at?: string | null;
  close_reason?: string | null;
  version: number;
}

/** 批13-W Tab0：装配清单总览（GET /capabilities/manifest） */
export interface AssemblyManifest {
  items: Record<string, unknown>;
  version: number;
  agent_key: string;
  capability_version: number;
  tool_universe: string[];
  tool_locked: string[];
  tool_default_allowed: string[];
  generics_note: string;
}

export const capabilitiesApi = {
  list: (config?: AxiosRequestConfig) => guardsClient.get('/capabilities', config),
  manifest: (config?: AxiosRequestConfig) => guardsClient.get('/capabilities/manifest', config),
  update: (capabilityId: string, body: { enabled?: boolean; params?: Record<string, unknown>; confirm?: boolean; close_reason?: string }, config?: AxiosRequestConfig) =>
    guardsClient.patch(`/capabilities/${capabilityId}`, body, config),
  probe: (capabilityId: string, config?: AxiosRequestConfig) =>
    guardsClient.post(`/capabilities/${capabilityId}/probe`, {}, config),
  events: (params?: { capability_id?: string; range?: string; page?: number; page_size?: number }, config?: AxiosRequestConfig) =>
    guardsClient.get('/capabilities/events', { params, ...config }),
  resetDefaults: (config?: AxiosRequestConfig) =>
    guardsClient.post('/capabilities/reset-defaults', {}, config),
};

// ===== 专家卡管理（专家地基①，/api/experts）=====
export interface ExpertCard {
  expert_id: string; name: string; tagline?: string | null; enabled: boolean;
  entry_kind: string; system_prompt: string; tools: string[]; skills: string[];
  memory: string[]; knowledge_sources: string[]; llm_connection_id?: string | null;
  icon?: string | null; description?: string | null;
  ui_config?: { placeholder?: string; suggestions?: string[]; welcome?: { title?: string; tagline?: string } };
  // 附件四 A-1：卡级 suggestions（门户/欢迎页可点建议）+params（调度参数白名单）——纯卡数据
  suggestions?: string[];
  params?: Record<string, unknown>;
  version: number; updated_by?: string | null; updated_at?: string | null; close_reason?: string | null;
}

export const expertsApi = {
  list: (params?: { enabled?: boolean }, config?: AxiosRequestConfig) =>
    guardsClient.get('/experts', { params, ...config }),
  get: (id: string, config?: AxiosRequestConfig) => guardsClient.get(`/experts/${id}`, config),
  create: (id: string, body: Record<string, unknown>, config?: AxiosRequestConfig) =>
    guardsClient.post(`/experts?id=${encodeURIComponent(id)}`, body, config),
  update: (id: string, body: Record<string, unknown>, config?: AxiosRequestConfig) =>
    guardsClient.patch(`/experts/${id}`, body, config),
  probe: (id: string, config?: AxiosRequestConfig) =>
    guardsClient.post(`/experts/${id}/probe`, {}, config),
  events: (params?: { expert_id?: string; page?: number; page_size?: number }, config?: AxiosRequestConfig) =>
    guardsClient.get('/experts/events', { params, ...config }),
};

// ===== 记忆管理（记忆插槽②，/api/memory——全部 admin）=====
export const memoryApi = {
  tree: (params: { expert_id: string; user: string; root?: string }, config?: AxiosRequestConfig) =>
    guardsClient.get('/memory/tree', { params, ...config }),
  file: (params: { expert_id: string; user: string; path: string; root?: string }, config?: AxiosRequestConfig) =>
    guardsClient.get('/memory/file', { params, ...config }),
  consolidate: (body: { expert_id: string; user: string }, config?: AxiosRequestConfig) =>
    guardsClient.post('/memory/consolidate', body, config),
  events: (params?: { expert_id?: string; kind?: string; limit?: number }, config?: AxiosRequestConfig) =>
    guardsClient.get('/memory/events', { params, ...config }),
};



// ---------------------------------------------------------------------------
// 权限重构T4（design §5.2/§5.3）：iam 管理面（用户/角色/审计）
// ---------------------------------------------------------------------------

export const iamApi = {
  getVocab: () => api.get('/iam/vocab'),
  listUsers: (params?: { kw?: string; page?: number; page_size?: number }) =>
    api.get('/iam/users', { params }),
  createUser: (data: { username: string; email?: string; display_name?: string; roles: string[]; password?: string }) =>
    api.post('/iam/users', data),
  patchUser: (sub: string, data: { is_active?: boolean; display_name?: string }) =>
    api.patch(`/iam/users/${sub}`, data),
  replaceUserRoles: (sub: string, roles: string[]) =>
    api.put(`/iam/users/${sub}/roles`, { roles }),
  listRoles: () => api.get('/iam/roles'),
  createRole: (data: { code: string; name: string; description?: string; default_permissions?: Record<string, string[]> }) =>
    api.post('/iam/roles', data),
  patchRole: (code: string, data: { name?: string; description?: string; default_permissions?: Record<string, string[]> }) =>
    api.patch(`/iam/roles/${code}`, data),
  deleteRole: (code: string) => api.delete(`/iam/roles/${code}`),
  listAudit: (params?: { resource_type?: string; decision?: string; page?: number; page_size?: number }) =>
    api.get('/iam/audit', { params }),
  checkPermission: (resourceType: string, action: string, resourceId = '') =>
    api.get('/auth/check', { params: { resource_type: resourceType, action, resource_id: resourceId } }),
  listGrants: (params: { principal_type: string; principal_id: string }) =>
    api.get('/auth/grants', { params }),
  revokeGrant: (id: number) => api.delete(`/auth/grant/${id}`),
};

export default api;