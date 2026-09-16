/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/lib/llm-options.ts，65 行）。
 * 随 MemoryRunPanel 随行移植（组内私有落位）。
 * 替换点：
 *  - apiFetch(apiUrl("/api/v1/settings/llm-options")) → fetch('/api/v1/settings/llm-options')
 *    （tupu vendor 已挂载，活探 200；同源 fetch 携带 cookie，与原 credentials:'include' 等价）；
 *  - 原仓依赖 web/lib/client-cache.ts 的 withClientCache/invalidateClientCache——tupu 未移植该
 *    lib 且禁止新增依赖，此处以模块级 Map 缓存内联等价实现（同 key 共享一次往返 + force 旁路 +
 *    invalidate 失效语义一致），替换点登记：待 client-cache 随其它批次并入时可换回；
 *  - LLMSelection 类型改从批8已移植的 pages/tutor/admin/unified-ws.ts 引入（同名字段
 *    profile_id/model_id，与原仓 unified-ws.ts 同源）。
 * 交互逐字未改。
 */
import type { LLMSelection } from "../tutor/admin/unified-ws";

export interface LLMOption extends LLMSelection {
  profile_name: string;
  model_name: string;
  model: string;
  provider: string;
  /** Human-readable provider name from the registry ("OpenRouter"). */
  provider_label?: string;
  context_window?: number;
  is_active_default: boolean;
}

export interface LLMOptionsResponse {
  active: LLMSelection | null;
  options: LLMOption[];
}

export function llmSelectionKey(selection: LLMSelection | null | undefined) {
  if (!selection?.profile_id || !selection.model_id) return "";
  return `${selection.profile_id}:${selection.model_id}`;
}

export function sameLLMSelection(
  a: LLMSelection | null | undefined,
  b: LLMSelection | null | undefined,
) {
  return llmSelectionKey(a) === llmSelectionKey(b);
}

// ── 内联 client-cache 等价（替换点登记，见头注）──────────────────────
const LLM_OPTIONS_CACHE_KEY = "llm-options:list";
const clientCache = new Map<string, Promise<unknown>>();

async function withClientCache<T>(
  key: string,
  loader: () => Promise<T>,
  options?: { force?: boolean },
): Promise<T> {
  if (!options?.force && clientCache.has(key)) {
    return clientCache.get(key) as Promise<T>;
  }
  const p = loader();
  clientCache.set(key, p);
  try {
    return await p;
  } catch (e) {
    clientCache.delete(key);
    throw e;
  }
}

function invalidateClientCache(key: string): void {
  clientCache.delete(key);
}

/** List the configured model profiles.
 *
 *  Cached so the many consumers that need the model list (composer, model
 *  picker, capability gate, partner forms) share one round-trip instead of
 *  each firing their own on mount. Editing a profile calls
 *  ``invalidateLLMOptionsCache``; pass ``force`` to bypass the cache. */
export async function listLLMOptions(options?: {
  force?: boolean;
}): Promise<LLMOptionsResponse> {
  return withClientCache<LLMOptionsResponse>(
    LLM_OPTIONS_CACHE_KEY,
    async () => {
      const response = await fetch("/api/v1/settings/llm-options", {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Failed to load LLM options: ${response.status}`);
      }
      const data = (await response.json()) as LLMOptionsResponse;
      return {
        active: data.active ?? null,
        options: Array.isArray(data.options) ? data.options : [],
      };
    },
    { force: options?.force },
  );
}

export function invalidateLLMOptionsCache(): void {
  invalidateClientCache(LLM_OPTIONS_CACHE_KEY);
}
