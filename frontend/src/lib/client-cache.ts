// IA批5 lib 补件：1:1 移植自 DeepTutor web/lib/client-cache.ts（批4 knowledge-api 内联版同源；
// 此处独立成模块供 lib/subagents-api 等消费——两份并存不共享 Map，与各自失效语义一致）。
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

export async function withClientCache<T>(
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

  // R5批⑤：归属校验——本请求的结算（回写/清删）仅当缓存槽仍是自己发起时创建的那个
  // entry 才生效。否则 force 换代/invalidate 清除后，旧在飞请求 resolve 会用陈旧数据
  // 覆盖新数据、reject 会误删新请求的有效条目或去重入口。
  const entry: CacheEntry<T> = { expiresAt: now + ttlMs };
  const promise = loader()
    .then((value) => {
      if (clientCache.get(key) === (entry as CacheEntry<unknown>)) {
        clientCache.set(key, {
          data: value,
          expiresAt: Date.now() + ttlMs,
        });
      }
      return value;
    })
    .catch((error) => {
      if (clientCache.get(key) === (entry as CacheEntry<unknown>)) {
        clientCache.delete(key);
      }
      throw error;
    });

  entry.promise = promise;
  clientCache.set(key, entry as CacheEntry<unknown>);

  return promise;
}

export function invalidateClientCache(prefix: string): void {
  // es5 目标无 downlevelIteration：Map.keys() 迭代改 Array.from（语义等价，D1 同款）。
  Array.from(clientCache.keys()).forEach((key) => {
    if (key.startsWith(prefix)) {
      clientCache.delete(key);
    }
  });
}
