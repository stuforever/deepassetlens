import axios from 'axios';

const V2_BASE_URL = '/api/v2';

const v2Api = axios.create({
  baseURL: V2_BASE_URL,
});

export interface SkillDTO {
  skill_id: string;
  skill_code: string;
  name: string;
  description?: string;
  skill_type: 'natural' | 'python' | 'sql' | 'http' | 'mixed' | 'claude';
  status: 'draft' | 'published' | 'disabled';
  current_version_id?: string;
  tags?: string[];
  priority: number;
  timeout: number;
  retry_policy?: Record<string, any>;
  resource_limits?: Record<string, any>;
  permissions?: Record<string, any>;
  app_type?: string;
  target_menu?: string;
  workspace_id?: string;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  updated_by?: string;
}

export interface SkillVersionDTO {
  version_id: string;
  version: string;
  status: 'draft' | 'active' | 'archived';
  input_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  content?: Record<string, any>;
  dependencies?: Record<string, any>;
  changelog?: string;
  released_by?: string;
  released_at?: string;
  created_at?: string;
  created_by?: string;
}

export interface ExecutionDTO {
  execution_code: string;
  status: 'running' | 'success' | 'failed' | 'timeout' | 'cancelled';
  output?: Record<string, any>;
  error?: string;
  duration_ms?: number;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  error_message?: string;
  created_via?: string;
  started_at?: string;
  completed_at?: string;
  skill_id?: string;
  version_id?: string;
}

export interface ExecutionResultDTO {
  execution_code: string;
  status: 'success' | 'failed';
  output?: Record<string, any>;
  duration_ms?: number;
  logs?: Array<{
    level: string;
    message: string;
    time: string;
  }>;
}

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export const skillV2Api = {
  listSkills: (params?: { status?: string; skill_type?: string; skip?: number; limit?: number }) =>
    v2Api.get<APIResponse<SkillDTO[]>>('/skills', { params }),

  getSkill: (skillId: string) =>
    v2Api.get<APIResponse<SkillDTO>>(`/skills/${skillId}`),

  getSkillByCode: (skillCode: string) =>
    v2Api.get<APIResponse<SkillDTO>>(`/skills/by-code/${skillCode}`),

  createSkill: (data: Partial<SkillDTO>) =>
    v2Api.post<APIResponse<{ skill_id: string; skill_code: string }>>('/skills', data),

  updateSkill: (skillId: string, data: Partial<SkillDTO>) =>
    v2Api.put<APIResponse<{ skill_id: string }>>(`/skills/${skillId}`, data),

  deleteSkill: (skillId: string) =>
    v2Api.delete<APIResponse>(`/skills/${skillId}`),

  publishSkill: (skillId: string) =>
    v2Api.post<APIResponse<{ skill_id: string; status: string }>>(`/skills/${skillId}/publish`),

  unpublishSkill: (skillId: string) =>
    v2Api.post<APIResponse<{ skill_id: string; status: string }>>(`/skills/${skillId}/unpublish`),

  listVersions: (skillId: string, status?: string) =>
    v2Api.get<APIResponse<SkillVersionDTO[]>>(`/skills/${skillId}/versions`, { params: { status } }),

  getVersion: (skillId: string, version: string) =>
    v2Api.get<APIResponse<SkillVersionDTO>>(`/skills/${skillId}/versions/${version}`),

  createVersion: (skillId: string, data: Partial<SkillVersionDTO>) =>
    v2Api.post<APIResponse<{ version_id: string; version: string }>>(`/skills/${skillId}/versions`, data),

  publishVersion: (skillId: string, version: string) =>
    v2Api.post<APIResponse<{ version_id: string; status: string }>>(`/skills/${skillId}/versions/${version}/publish`),

  createExecution: (skillId: string, data: { input_payload: Record<string, any>; version?: string }) =>
    v2Api.post<APIResponse<ExecutionResultDTO>>(`/skills/${skillId}/executions`, data),

  listExecutions: (skillId: string, params?: { status?: string; skip?: number; limit?: number }) =>
    v2Api.get<APIResponse<ExecutionDTO[]>>(`/skills/${skillId}/executions`, { params }),

  getExecution: (executionCode: string) =>
    v2Api.get<APIResponse<ExecutionDTO>>(`/skills/executions/${executionCode}`),

  getTools: (params?: { skill_type?: string; app_type?: string }) =>
    v2Api.get<APIResponse<any[]>>('/tools', { params }),

  createDebugSession: (data: { skill_id: string; input_payload?: Record<string, any>; debug_mode?: string; breakpoints?: number[] }) =>
    v2Api.post<APIResponse<{ session_code: string }>>('/debug/sessions', data),

  debugStep: (sessionCode: string) =>
    v2Api.post<APIResponse<any>>(`/debug/sessions/${sessionCode}/step`),

  getDebugSession: (sessionCode: string) =>
    v2Api.get<APIResponse<any>>(`/debug/sessions/${sessionCode}`),

  getDebugVariables: (sessionCode: string) =>
    v2Api.get<APIResponse<any>>(`/debug/sessions/${sessionCode}/variables`),

  getDebugLogs: (sessionCode: string) =>
    v2Api.get<APIResponse<any[]>>(`/debug/sessions/${sessionCode}/logs`),

  setBreakpoint: (sessionCode: string, lineNumber: number) =>
    v2Api.post<APIResponse>(`/debug/sessions/${sessionCode}/breakpoints`, { session_code: sessionCode, line_number: lineNumber }),

  removeBreakpoint: (sessionCode: string, lineNumber: number) =>
    v2Api.delete<APIResponse>(`/debug/sessions/${sessionCode}/breakpoints/${lineNumber}`),

  terminateDebugSession: (sessionCode: string) =>
    v2Api.delete<APIResponse>(`/debug/sessions/${sessionCode}`),

  // 模板
  listTemplates: () =>
    v2Api.get<APIResponse<any[]>>('/templates'),

  getTemplate: (id: string) =>
    v2Api.get<APIResponse<any>>(`/templates/${id}`),

  applyTemplate: (id: string) =>
    v2Api.post<APIResponse<{ skill_id: string; skill_code: string }>>(`/templates/${id}/apply`),

  // 导入导出
  exportSkillZip: (skillId: string) =>
    v2Api.get<Blob>(`/skills/${skillId}/export`, { responseType: 'blob' }),

  importSkillZip: (file: File, skillId?: string) => {
    const formData = new FormData();
    formData.append('uploaded_file', file);
    if (skillId) formData.append('skill_id', skillId);
    return v2Api.post<APIResponse<{ skill_id: string; skill_code: string; imported_versions: number }>>('/skills/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // 异步执行
  createExecutionAsync: (skillId: string, data: { input_payload: Record<string, any>; version?: string }) =>
    v2Api.post<APIResponse<ExecutionDTO>>(`/skills/${skillId}/executions/async`, data),

  // Worker 管理
  getWorkerStatus: () =>
    v2Api.get<APIResponse<any>>('/worker/status'),

  startWorker: () =>
    v2Api.post<APIResponse<any>>('/worker/start'),

  stopWorker: () =>
    v2Api.post<APIResponse<any>>('/worker/stop'),

  publishSkillWithApproval: (skillId: string, comment: string) =>
    v2Api.post<APIResponse<{ skill_id: string; approval_status: string }>>(`/skills/${skillId}/publish/approval`, { data: { comment } }),

  listSkillFiles: (skillId: string) =>
    v2Api.get<APIResponse<any[]>>(`/skills/${skillId}/files`),

  readSkillFile: (skillId: string, path: string) =>
    v2Api.get<APIResponse<{ path: string; content: string }>>(`/skills/${skillId}/files/content`, { params: { path } }),

  writeSkillFile: (skillId: string, path: string, content: string) =>
    v2Api.put<APIResponse<{ path: string; message: string }>>(`/skills/${skillId}/files/content`, { path, content }),

  deleteSkillFile: (skillId: string, path: string) =>
    v2Api.delete<APIResponse>(`/skills/${skillId}/files/content`, { params: { path } }),

  getSkillMd: (skillId: string) =>
    v2Api.get<APIResponse<any>>(`/skills/${skillId}/skill-md`),

  // 技能类型管理（1.1 动态配置）
  listSkillTypes: () =>
    v2Api.get<APIResponse<any[]>>('/skill-types'),

  createSkillType: (data: { type_code: string; name: string; description?: string; icon?: string; color?: string; ext?: string }) =>
    v2Api.post<APIResponse<any>>('/skill-types', data),

  updateSkillType: (typeCode: string, data: any) =>
    v2Api.put<APIResponse<any>>(`/skill-types/${typeCode}`, data),

  disableSkillType: (typeCode: string) =>
    v2Api.put<APIResponse<any>>(`/skill-types/${typeCode}/disable`),

  // 工具接口（3.2 risk_level 过滤）
  getToolsV2: (params?: { skill_type?: string; risk_level?: string }) =>
    v2Api.get<APIResponse<any[]>>('/tools/v2', { params }),

  // 版本快照（6.2）
  snapshotVersion: (skillId: string, version: string) =>
    v2Api.post<APIResponse<any>>(`/skills/${skillId}/versions/${version}/snapshot`),

  // 密钥柜（5.2）
  listSecrets: () =>
    v2Api.get<APIResponse<any[]>>('/secrets'),

  upsertSecret: (data: { key_name: string; key_value: string; description?: string }) =>
    v2Api.post<APIResponse<any>>('/secrets', data),

  deleteSecret: (keyName: string) =>
    v2Api.delete<APIResponse>(`/secrets/${keyName}`),

  // 定时调度（4.3）
  listSchedules: (status?: string) =>
    v2Api.get<APIResponse<any[]>>('/schedules', { params: { status } }),

  createSchedule: (data: { skill_id: string; name: string; cron_expression: string; input_payload?: any }) =>
    v2Api.post<APIResponse<any>>('/schedules', data),

  pauseSchedule: (scheduleCode: string) =>
    v2Api.put<APIResponse<any>>(`/schedules/${scheduleCode}/pause`),

  resumeSchedule: (scheduleCode: string) =>
    v2Api.put<APIResponse<any>>(`/schedules/${scheduleCode}/resume`),

  deleteSchedule: (scheduleCode: string) =>
    v2Api.delete<APIResponse>(`/schedules/${scheduleCode}`),
};

export default v2Api;
