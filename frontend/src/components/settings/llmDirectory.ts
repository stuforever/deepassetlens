/**
 * 引擎批8 8.1：/llm-config 数据面切③连接目录（LLM 合一反转——③唯一源，spec §七）。
 *
 * 适配器职责：③连接行（kg_llm_connection_configs，api/llm_admin.py CRUD）↔ vendor
 * catalog services.llm 块（SettingsContext CatalogService 形状）双向映射，使
 * ServiceConfigEditor UI 1:1 零改地跑在③数据面上。
 *
 * 映射表（实测依据：dt_llm_sync.py L32-49 vendor→③ 方向实证 + LLMConnectionCreate
 * llm_admin.py L17-32 + _serialize_conn L97-116）：
 *   ③行 → profile×model：
 *     分组键   = extra_config.profile_key ?? row.id（一行③=一模型；同 profile_key 组=一 profile 多模型）
 *     name     = extra_config.profile_name ?? row.name
 *     binding  = 'openai'（③ provider 'openai_compatible' 同义，dt_llm_sync L37 实证）
 *     base_url = row.base_url          api_key = row.api_key ?? ''
 *     api_version/extra_headers = extra_config 同名字段
 *     model.id = `${row.id}::m`        model.name/model.model = row.model_name
 *     context_window/source/detected_at = extra_config 同名字段
 *     active_profile_id/active_model_id = is_default 行（无 default→首行）
 *   vendor 块 → ③CRUD：
 *     name = `${profile.name}·${model.name}`（dt_llm_sync L34 命名约定）
 *     新建默认：provider 'openai_compatible'/capability 'chat'/api_path '/chat/completions'/
 *               temperature '0.2'/max_tokens 512/timeout_seconds 60
 *     is_default =（profile+model 双激活）；置 True 时后端自动清其余 default（llm_admin L235-236 实证）
 *     删除 = 上一帧行集里不在本帧 model 集合的行
 *
 * 差异登记（引擎件差异台账 批8）：vendor llm 块冻结（写入时回填防合成形状污染 vendor
 * catalog）；/settings/llm-options 下拉仍读 vendor catalog（冻结快照）——诚实账登记。
 */
import { llmAdminApi } from '../../services/api';
import type { CatalogService, CatalogProfile, CatalogModel } from './SettingsContext';

export interface LLMConnectionRow {
  id: string;
  name: string;
  provider: string;
  capability: string;
  description: string | null;
  base_url: string;
  api_path: string | null;
  api_key: string | null;
  model_name: string;
  is_default: boolean;
  enabled: boolean;
  temperature: string | null;
  max_tokens: number | null;
  timeout_seconds: number | null;
  extra_config: Record<string, unknown> | null;
  capabilities: Record<string, boolean> | null;
  created_at: string | null;
}

const MODEL_ID_SUFFIX = '::m';
const NEW_CONNECTION_DEFAULTS = {
  provider: 'openai_compatible',
  capability: 'chat',
  api_path: '/chat/completions',
  temperature: '0.2',
  max_tokens: 512,
  timeout_seconds: 60,
} as const;

function rowExtra(row: LLMConnectionRow): Record<string, unknown> {
  return row.extra_config && typeof row.extra_config === 'object' ? row.extra_config : {};
}

function strVal(v: unknown, fallback = ''): string {
  return typeof v === 'string' ? v : fallback;
}

function parseExtraHeaders(v: unknown): Record<string, string> {
  if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, string>;
  if (typeof v === 'string' && v.trim()) {
    try {
      const parsed = JSON.parse(v);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
    } catch {
      // draft 中间态字符串（未成 JSON）按空表处理
    }
  }
  return {};
}

/** 拉取③连接行（llmAdminApi → {code,data}；失败抛异常由调用方决定降级）。 */
export async function fetchLlmConnectionRows(): Promise<LLMConnectionRow[]> {
  const resp = await llmAdminApi.getConnections();
  const payload = resp.data as { code?: number; data?: LLMConnectionRow[] };
  return Array.isArray(payload?.data) ? payload.data : [];
}

/** ③行集 → vendor services.llm 块（CatalogService 形状，ServiceConfigEditor 零改消费）。 */
export function rowsToLlmService(rows: LLMConnectionRow[]): CatalogService {
  const groups = new Map<string, LLMConnectionRow[]>();
  for (const row of rows) {
    const key = strVal(rowExtra(row).profile_key, row.id);
    const bucket = groups.get(key);
    if (bucket) bucket.push(row);
    else groups.set(key, [row]);
  }

  const profiles: CatalogProfile[] = [];
  for (const [key, bucket] of groups) {
    const head = bucket[0];
    const extra = rowExtra(head);
    const models: CatalogModel[] = bucket.map((row) => {
      const rowExtraCfg = rowExtra(row);
      const model: CatalogModel = {
        id: `${row.id}${MODEL_ID_SUFFIX}`,
        name: row.model_name || row.name,
        model: row.model_name,
      };
      if (rowExtraCfg.context_window != null) model.context_window = String(rowExtraCfg.context_window);
      if (rowExtraCfg.context_window_source != null) model.context_window_source = String(rowExtraCfg.context_window_source);
      if (rowExtraCfg.context_window_detected_at != null) model.context_window_detected_at = String(rowExtraCfg.context_window_detected_at);
      return model;
    });
    profiles.push({
      id: key,
      name: strVal(extra.profile_name, head.name),
      binding: 'openai',
      base_url: head.base_url,
      api_key: head.api_key ?? '',
      api_version: strVal(extra.api_version),
      extra_headers: parseExtraHeaders(extra.extra_headers),
      models,
    });
  }

  const defaultRow = rows.find((r) => r.is_default) ?? rows[0] ?? null;
  let activeProfileId: string | null = null;
  let activeModelId: string | null = null;
  if (defaultRow) {
    activeProfileId = strVal(rowExtra(defaultRow).profile_key, defaultRow.id);
    activeModelId = `${defaultRow.id}${MODEL_ID_SUFFIX}`;
  }
  return { active_profile_id: activeProfileId, active_model_id: activeModelId, profiles };
}

/** 便捷封装：拉取并转换；③不可达返回 null（调用方退回 vendor 数据面）。 */
export async function loadLlmDirectory(): Promise<{ rows: LLMConnectionRow[]; block: CatalogService } | null> {
  try {
    const rows = await fetchLlmConnectionRows();
    return { rows, block: rowsToLlmService(rows) };
  } catch (err) {
    console.error('[llmDirectory] ③连接目录加载失败:', err);
    return null;
  }
}

function rowIdFromModelId(modelId: string): string | null {
  return modelId.endsWith(MODEL_ID_SUFFIX) ? modelId.slice(0, -MODEL_ID_SUFFIX.length) : null;
}

/** 生成与既有行名不冲突的连接名。 */
function uniqueName(base: string, taken: Set<string>): string {
  if (!taken.has(base)) return base;
  let n = 2;
  while (taken.has(`${base}(${n})`)) n += 1;
  return `${base}(${n})`;
}

/** 档名→连接名约定：单模型档=档名（保留用户既有名如 '4coding'）；多模型档=档名·模型名。 */
function connNameFor(profileName: string, modelCount: number, modelName: string): string {
  return modelCount > 1 ? `${profileName}·${modelName || '模型'}` : profileName;
}

/**
 * vendor services.llm 块（用户草稿）→ ③CRUD 落库，返回落库后的新块+新行集。
 * prevRows = 上一次同步的③行集（删除判定与行 id 对账基准）。
 * 命名契约：更新时仅当档名/结构实际变化才改连接名（E-28：整写 name 会把用户既有
 * 名 '4coding' 重写成 '4coding·模型'，破坏 seed/教学域既有引用——已修正）。
 */
export async function saveLlmDirectory(
  next: CatalogService,
  prevRows: LLMConnectionRow[],
): Promise<{ rows: LLMConnectionRow[]; block: CatalogService }> {
  // 三轨M10(:222)：逐行操作包 try/catch——单行失败计数告警不再整体抛出半完成态
  const saveErrors: string[] = [];
  const prevById = new Map(prevRows.map((r) => [r.id, r]));
  const nextRowIds = new Set<string>();
  const takenNames = new Set<string>();
  const defaultProfileId = next.active_profile_id;
  const defaultModelId = next.active_model_id ?? null;

  for (const profile of next.profiles) {
    const isNewProfile = !prevRows.some((r) => strVal(rowExtra(r).profile_key, r.id) === profile.id);
    const profileKey = isNewProfile
      ? (globalThis.crypto?.randomUUID?.() ?? `pk_${Date.now()}_${Math.random().toString(16).slice(2)}`)
      : profile.id;
    const extraHeaders = parseExtraHeaders(profile.extra_headers);
    for (const model of profile.models) {
      const existingId = rowIdFromModelId(model.id);
      const rowId = existingId && prevById.has(existingId) ? existingId : null;
      const isDefault = profile.id === defaultProfileId && model.id === defaultModelId;
      const desiredName = connNameFor(profile.name, profile.models.length, model.name || model.model);
      // 更新分支：连接名保留原名（desiredName===prevRow.name 时零改名），防止既有名被重写
      const prevRow = rowId ? prevById.get(rowId) : undefined;
      const connName = prevRow
        ? desiredName !== prevRow.name
          ? uniqueName(desiredName, takenNames)
          : prevRow.name
        : uniqueName(desiredName, takenNames);
      const baseFields = {
        name: connName,
        base_url: profile.base_url,
        api_key: profile.api_key || null,
        model_name: model.model,
        is_default: isDefault,
        extra_config: {
          source: 'llm-config',
          profile_key: profileKey,
          profile_name: profile.name,
          api_version: profile.api_version ?? '',
          extra_headers: extraHeaders,
          ...(model.context_window != null ? { context_window: model.context_window } : {}),
          ...(model.context_window_source != null ? { context_window_source: model.context_window_source } : {}),
          ...(model.context_window_detected_at != null ? { context_window_detected_at: model.context_window_detected_at } : {}),
        },
      };
      try {
        if (rowId) {
          takenNames.add(connName);
          nextRowIds.add(rowId);
          // 交棒 §5.3(b)：update=原始行+覆盖映射字段——extra_config 先铺原值再覆盖
          // 映射键，保住 4coding 行 mode_profiles 等既有键不被抹掉。
          await llmAdminApi.updateConnection(rowId, {
            ...baseFields,
            extra_config: { ...rowExtra(prevRow!), ...baseFields.extra_config },
          });
        } else {
          const created = await llmAdminApi.createConnection({
            ...NEW_CONNECTION_DEFAULTS,
            ...baseFields,
            enabled: true,
            description: '引擎批8：/llm-config ③直连管理',
          });
          const createdRow = (created.data as { data?: LLMConnectionRow })?.data;
          if (createdRow) {
            takenNames.add(createdRow.name);
            nextRowIds.add(createdRow.id);
          } else {
            saveErrors.push(`create ${profile.name}: 响应缺行`);
          }
        }
      } catch (e) {
        saveErrors.push(`${rowId ? 'update' : 'create'} ${profile.name}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
  }

  for (const row of prevRows) {
    if (!nextRowIds.has(row.id)) {
      try {
        await llmAdminApi.deleteConnection(row.id);
      } catch (e) {
        // 三轨M10(:242)：并发已删（404）不再中途炸——记录后继续对账
        saveErrors.push(`delete ${row.name}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
  }

  const rows = await fetchLlmConnectionRows();
  if (saveErrors.length) {
    // eslint-disable-next-line no-console
    console.warn('[llmDirectory] 保存存在失败行（部分成功可恢复）:', saveErrors);
  }
  return { rows, block: rowsToLlmService(rows) };
}

/** 块级深比较（同构 JSON 字符串比较——块由本适配器确定性生成）。 */
export function llmBlocksEqual(a: CatalogService, b: CatalogService): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}
