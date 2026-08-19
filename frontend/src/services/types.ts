/**
 * 统一 API 响应壳与核心 DTO。
 *
 * 后端常规返回 `{ data: T }`，错误时返回 `{ detail?: string }`（由 http.ts 统一提示读取）。
 * 各服务层（api.ts / skillV2Api.ts / dataIntelligenceApi.ts）应复用这里的类型，逐步收敛 `any`。
 */
export interface ApiResp<T> {
  code?: number;
  data: T;
  message?: string;
  detail?: string;
}

/** 数据源（DataSourceConfig 与 ModelTreeManager physical_table 绑定共用） */
export interface DataSource {
  id: string;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  description?: string;
  is_default: boolean;
  enabled: boolean;
  doris_catalog_name?: string;
}

export interface DataSourceInput {
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password?: string;
  description?: string;
  is_default?: boolean;
  enabled?: boolean;
  doris_catalog_name?: string;
}

/** 概念/实体（conceptApi / entityApi 高频域，先定型最常用字段） */
export interface ConceptDTO {
  id: string;
  code: string;
  name: string;
  level: number;
  parent_id?: string | null;
  description?: string;
  display_name?: string;
  sort_order?: number;
}

export interface EntityDTO {
  id: string;
  code: string;
  name: string;
  en_name?: string;
  source_mode?: 'physical_table' | 'sql_integration' | 'api_integration';
  integration_sql?: string;
  description?: string;
}

export interface EntityInput {
  code?: string;
  name?: string;
  en_name?: string;
  source_mode?: EntityDTO['source_mode'];
  integration_sql?: string;
  description?: string;
}
