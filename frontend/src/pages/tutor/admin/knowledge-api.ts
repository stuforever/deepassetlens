/**
 * knowledge-api.ts —— 使用面复刻（1:1 复刻被引用链）
 *
 * 来源：DeepTutor web/lib/knowledge-api.ts（858 行）
 * 复刻范围：仅保留 BookCreator 引用链上的导出——
 *   - 函数：listKnowledgeBases
 *   - 类型：KnowledgeBaseSummary
 * 裁剪掉的导出（BookCreator 未使用）：listRagProviders / getKnowledgeUploadPolicy /
 *   invalidateKnowledgeCaches / getPageIndexConfig / updatePageIndexConfig / getLlamaIndexConfig /
 *   updateLlamaIndexConfig / getGraphRagConfig / updateGraphRagConfig / getLightRagConfig /
 *   updateLightRagConfig / getEnginePreflight / getEngineModelOptions / setEngineActiveModel /
 *   updateRagProviderMode / listKnowledgeBaseFiles / knowledgeBaseFilePath /
 *   knowledgeBaseFilePreviewTextPath / createKnowledgeBase / connectObsidianVault /
 *   probeLinkedFolder / connectLinkedFolder / probeLightRagServer / connectLightRagServer /
 *   uploadKnowledgeBaseFiles / createKbFolder / moveKbFile / deleteKbFile /
 *   setDefaultKnowledgeBase / reindexKnowledgeBase / retryKnowledgeBase / deleteKnowledgeBase
 *   以及 RagProviderSummary / PageIndexConfig / LlamaIndexConfig / GraphRagConfig /
 *   LightRagConfig / PreflightCheck / EnginePreflight / ModelOption / ModelKindOptions /
 *   ModelOptionsByKind / KnowledgeUploadPolicy / KnowledgeBaseFile / KnowledgeTaskResponse /
 *   LinkedFolderProbe / LightRagServerProbe 等类型与常量。
 *
 * 替换点：
 *   1. apiFetch(apiUrl("/api/v1/knowledge/list")) → fetch('/api/v1/knowledge/list')
 *      （tupu 同源代理转发，fetch 默认 same-origin 携带 cookie，与原 credentials:'include' 等价；
 *        原 apiFetch 的 401→/login 跳转为 DeepTutor 鉴权专属，不复刻）
 *   2. withClientCache / invalidateClientCache 来自 @/lib/client-cache，
 *      此处内联等价实现（逻辑逐字取自 DeepTutor web/lib/client-cache.ts）
 */

// ── 内联：DeepTutor web/lib/client-cache.ts（逐字逻辑） ──────────────────

type CacheEntry<T> = {
  data?: T;
  promise?: Promise<T>;
  expiresAt: number;
};

const clientCache = new Map<string, CacheEntry<unknown>>();

interface CacheOptions {
  ttlMs?: number;
  force?: boolean;
}

async function withClientCache<T>(
  key: string,
  loader: () => Promise<T>,
  options: CacheOptions = {},
): Promise<T> {
  const { ttlMs = 30_000, force = false } = options;

  if (typeof window === "undefined") {
    return loader();
  }

  const now = Date.now();
  const cached = clientCache.get(key) as CacheEntry<T> | undefined;
  if (!force && cached) {
    if (cached.data !== undefined && cached.expiresAt > now) {
      return cached.data;
    }
    if (cached.promise) {
      return cached.promise;
    }
  }

  const promise = loader()
    .then((value) => {
      clientCache.set(key, {
        data: value,
        expiresAt: Date.now() + ttlMs,
      });
      return value;
    })
    .catch((error) => {
      clientCache.delete(key);
      throw error;
    });

  clientCache.set(key, {
    promise,
    expiresAt: now + ttlMs,
  });

  return promise;
}

// ── 类型（逐字保留） ─────────────────────────────────────────────────────

export interface KnowledgeBaseSummary {
  id?: string;
  name: string;
  is_default?: boolean;
  status?: string;
  path?: string;
  metadata?: Record<string, unknown>;
  progress?: Record<string, unknown>;
  statistics?: Record<string, unknown>;
  source?: "admin" | "user";
  assigned?: boolean;
  read_only?: boolean;
  provenance_label?: string;
  available?: boolean;
}

// ── 函数（函数体/fetch 路径逐字保留） ────────────────────────────────────

const KNOWLEDGE_CACHE_PREFIX = "knowledge:";

export async function listKnowledgeBases(options?: { force?: boolean }) {
  return withClientCache<KnowledgeBaseSummary[]>(
    `${KNOWLEDGE_CACHE_PREFIX}list`,
    async () => {
      const response = await fetch("/api/v1/knowledge/list", {
        cache: "no-store",
      });
      const data = await response.json();
      return Array.isArray(data)
        ? data
        : Array.isArray(data?.knowledge_bases)
          ? data.knowledge_bases
          : [];
    },
    {
      force: options?.force,
    },
  );
}
