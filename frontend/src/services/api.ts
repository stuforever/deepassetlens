import axios from 'axios';
import { getStoredToken, clearToken, isTokenValid } from '../auth/oidc';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Authentik Bearer 自动注入
api.interceptors.request.use((config) => {
  const t = getStoredToken();
  if (t && isTokenValid(t)) {
    config.headers = config.headers || {};
    (config.headers as any)['Authorization'] = `${t.token_type} ${t.access_token}`;
  }
  return config;
});

// 401 → 清 token 跳登录
api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    if (error?.response?.status === 401) {
      clearToken();
      // 不 reload 主流程内的所有请求，让 AuthGate 重入；或硬跳一次首页
      if (window.location.pathname !== '/auth/callback') {
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  },
);

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
  create: (data: { name: string; description?: string }) => api.post('/knowledge-bases', data),
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
  deleteConnection: (id: string) => api.delete(`/llm-connections/${id}`),
  testConnection: (id: string) => api.post(`/llm-connections/${id}/test`),
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
  getConfig: () => api.get('/doris/config'),
  putConfig: (cfg: Record<string, any>) => api.put('/doris/config', cfg),
  testConnection: (cfg?: Record<string, any>) => api.post('/doris/config/test', cfg || {}),
  listCatalogs: () => api.get('/doris/catalogs'),
  createCatalog: (c: Record<string, any>) => api.post('/doris/catalogs', c),
  deleteCatalog: (name: string) => api.delete(`/doris/catalogs/${encodeURIComponent(name)}`),
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

export default api;
