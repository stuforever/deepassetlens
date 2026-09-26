/**
 * E3 离线答题 outbox（M12）——原仓 lib/h5-outbox.ts 1:1 移植。
 * 断网时本地暂存 grade-exercise 上报，联网后保序重放（FSRS 状态机依赖顺序）；
 * 后端以 attempt_id 幂等，保证副作用只发生一次。
 *
 * IndexedDB：db `dsh-h5`，store `outbox`（keyPath: attempt_id）。
 */

export interface OutboxEntry {
  attempt_id: string;
  url: string;
  body: Record<string, unknown>;
  ts: number;
  retries: number;
}

const DB_NAME = "dsh-h5";
const STORE = "outbox";
const MAX_RETRIES = 5;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("no indexeddb"));
      return;
    }
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "attempt_id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function txDone(db: IDBDatabase, mode: IDBTransactionMode, work: (s: IDBObjectStore) => IDBRequest | void): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const store = tx.objectStore(STORE);
    work(store);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function enqueue(entry: OutboxEntry): Promise<void> {
  try {
    const db = await openDb();
    await txDone(db, "readwrite", (s) => s.put(entry));
    db.close();
  } catch {
    /* 无 IndexedDB 时不阻塞学习 */
  }
}

export async function list(): Promise<OutboxEntry[]> {
  const db = await openDb();
  try {
    const entries = await new Promise<OutboxEntry[]>((resolve, reject) => {
      const req = db.transaction(STORE, "readonly").objectStore(STORE).getAll();
      req.onsuccess = () => resolve((req.result || []) as OutboxEntry[]);
      req.onerror = () => reject(req.error);
    });
    return entries.sort((a, b) => a.ts - b.ts);
  } finally {
    db.close();
  }
}

export async function count(): Promise<number> {
  try {
    return (await list()).length;
  } catch {
    return 0;
  }
}

async function remove(attemptId: string): Promise<void> {
  try {
    const db = await openDb();
    await txDone(db, "readwrite", (s) => s.delete(attemptId));
    db.close();
  } catch {
    /* ignore */
  }
}

/**
 * 串行重放 outbox。成功删除；失败 retries+1（指数退避由触发方间隔控制），
 * >=MAX_RETRIES 放弃并删除（打 console）。返回成功条数。
 */
export async function replay(): Promise<number> {
  let entries: OutboxEntry[] = [];
  try {
    entries = await list();
  } catch {
    return 0;
  }
  if (entries.length === 0) return 0;
  let ok = 0;
  for (const e of entries) {
    try {
      const res = await fetch(e.url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(e.body),
      });
      if (res.ok) {
        await remove(e.attempt_id);
        ok += 1;
        continue;
      }
      // 网络可达但业务拒绝（如访问码 401）：重试也可能失败，仅递增计数
      const nextFail: OutboxEntry = { ...e, retries: (e.retries || 0) + 1, ts: Date.now() };
      if (nextFail.retries >= MAX_RETRIES) {
        await remove(e.attempt_id);
        console.warn("[h5-outbox] drop after retries", e.attempt_id);
      } else {
        try {
          const dbFail = await openDb();
          await txDone(dbFail, "readwrite", (s) => s.put(nextFail));
          dbFail.close();
        } catch {
          /* ignore */
        }
      }
      continue;
    } catch {
      // C-修复：仍离线不计重试、保留条目——原实现离线也递增 retries，
      // 周期 replay 下连续 5 轮离线会把暂存的答题上报永久删除（学习记录丢失）
      continue;
    }
  }
  return ok;
}
