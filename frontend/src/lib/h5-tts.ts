"use client";

/**
 * T2（第十二篇）：H5 统一朗读管理器。
 *
 * 优先级 = me 页引擎设置（h5_tts_engine: auto[默认]/browser/server）× T1 检测结果：
 * - 浏览器路径：speechSynthesis 原逻辑（含语速设置）——零成本；
 * - 服务端路径：POST /api/v1/voice/tts（带 u）→ blob → <audio> 播放；
 *   · IndexedDB 按文本 hash 缓存 blob，LRU 50 条（翻回来不重复合成）；
 *   · 400（未配 TTS provider）→ toast 明说，回落浏览器/静默。
 *
 * 替换点：chat speak()、wrongbook 朗读、usePageSpeech（书阅读器）统一走这里。
 */

import { apiUrl } from "./api";
import { getH5User } from "./h5-utils";

export type H5TtsEngine = "auto" | "browser" | "server";

export function readStoredSpeechRate(): number {
  try {
    const raw = localStorage.getItem("h5_speech_rate");
    const n = raw ? parseFloat(raw) : NaN;
    return Number.isFinite(n) && n >= 0.5 && n <= 2 ? n : 1;
  } catch {
    return 1;
  }
}

export function readStoredTtsEngine(): H5TtsEngine {
  try {
    const v = localStorage.getItem("h5_tts_engine");
    if (v === "browser" || v === "server") return v;
  } catch {
    /* ignore */
  }
  return "auto";
}

/** 浏览器是否有中文音色（同步首查；Chrome 异步到齐前可能为空，调用方多以 auto 语义容忍） */
export function hasChineseVoiceSync(): boolean {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
  try {
    return (window.speechSynthesis.getVoices() || []).some((v) =>
      (v.lang || "").toLowerCase().startsWith("zh"),
    );
  } catch {
    return false;
  }
}

// --------------------------------------------------------------------------- //
// 失败 toast（T2 验收：未配 provider → 明确提示，不再静默）
// --------------------------------------------------------------------------- //

let toastTimer: ReturnType<typeof setTimeout> | null = null;
export function showTtsToast(message: string) {
  if (typeof document === "undefined") return;
  try {
    const old = document.getElementById("dsh-h5-tts-toast");
    if (old) old.remove();
    const el = document.createElement("div");
    el.id = "dsh-h5-tts-toast";
    el.textContent = message;
    el.setAttribute("data-testid", "h5-tts-toast");
    el.style.cssText =
      "position:fixed;left:50%;bottom:96px;transform:translateX(-50%);z-index:9999;" +
      "background:rgba(15,23,42,.92);color:#fff;padding:8px 14px;border-radius:12px;" +
      "font-size:12px;max-width:80vw;box-shadow:0 4px 14px rgba(0,0,0,.25);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
    document.body.appendChild(el);
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.remove();
      toastTimer = null;
    }, 2600);
  } catch {
    /* ignore */
  }
}

// --------------------------------------------------------------------------- //
// IndexedDB blob 缓存（LRU 50）
// --------------------------------------------------------------------------- //

const DB_NAME = "dsh-h5-tts";
const STORE = "audio";
const LRU_MAX = 50;

function fnv1a(text: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(36) + "_" + text.length.toString(36);
}

function openDb(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    try {
      if (typeof indexedDB === "undefined") return resolve(null);
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "key" });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function cacheGet(key: string): Promise<Blob | null> {
  const db = await openDb();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(key);
      req.onsuccess = () => {
        const row = req.result as { blob: Blob } | undefined;
        resolve(row?.blob ?? null);
      };
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function cachePut(key: string, blob: Blob): Promise<void> {
  const db = await openDb();
  if (!db) return;
  await new Promise<void>((resolve) => {
    try {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put({ key, blob, ts: Date.now() });
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    } catch {
      resolve();
    }
  });
  // LRU 裁剪：按 ts 保留最近 LRU_MAX 条
  try {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    const allReq = store.getAll();
    allReq.onsuccess = () => {
      const rows = (allReq.result || []) as { key: string; ts: number }[];
      if (rows.length <= LRU_MAX) return;
      rows.sort((a, b) => (a.ts || 0) - (b.ts || 0));
      for (const r of rows.slice(0, rows.length - LRU_MAX)) {
        try {
          store.delete(r.key);
        } catch {
          /* ignore */
        }
      }
    };
  } catch {
    /* ignore */
  }
}

// --------------------------------------------------------------------------- //
// 服务端合成
// --------------------------------------------------------------------------- //

export async function serverTts(text: string): Promise<Blob | null> {
  try {
    const u = getH5User();
    const qs = u ? `?u=${encodeURIComponent(u)}` : "";
    const res = await fetch(apiUrl(`/api/v1/voice/tts${qs}`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 2000) }),
    });
    if (!res.ok) {
      if (res.status === 400) {
        showTtsToast("服务端朗读未配置（桌面「设置」→ TTS）");
      } else {
        showTtsToast(`服务端朗读失败（${res.status}）`);
      }
      return null;
    }
    return await res.blob();
  } catch {
    showTtsToast("服务端朗读网络错误");
    return null;
  }
}

/**
 * 静默版服务端合成（供 usePageSpeech 段播用）：不弹 toast（段播失败会自动回落浏览器）。
 * 显式传 u（hook 不在 h5 用户上下文里时也能隔离）。
 */
export async function serverTtsToBlob(
  text: string,
  explicitU?: string,
): Promise<Blob> {
  const u = explicitU || getH5User();
  const qs = u ? `?u=${encodeURIComponent(u)}` : "";
  const res = await fetch(apiUrl(`/api/v1/voice/tts${qs}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text.slice(0, 2000) }),
  });
  if (!res.ok) {
    throw new Error(`tts ${res.status}`);
  }
  return await res.blob();
}

// --------------------------------------------------------------------------- //
// 播放控制（浏览器 utterance / 服务端 audio 二选一，全局可停）
// --------------------------------------------------------------------------- //

let currentUtterance: SpeechSynthesisUtterance | null = null;
let currentAudio: HTMLAudioElement | null = null;
let currentObjectUrl: string | null = null;

export function h5StopSpeak() {
  try {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  } catch {
    /* ignore */
  }
  currentUtterance = null;
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.src = "";
    } catch {
      /* ignore */
    }
    currentAudio = null;
  }
  if (currentObjectUrl) {
    try {
      URL.revokeObjectURL(currentObjectUrl);
    } catch {
      /* ignore */
    }
    currentObjectUrl = null;
  }
}

function speakBrowser(text: string, onDone?: () => void): boolean {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    onDone?.();
    return false;
  }
  try {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "zh-CN";
    utter.rate = readStoredSpeechRate();
    if (onDone) {
      utter.onend = () => onDone();
      utter.onerror = () => onDone();
    }
    currentUtterance = utter;
    window.speechSynthesis.speak(utter);
    return true;
  } catch {
    onDone?.();
    return false;
  }
}

async function speakServer(text: string, onDone?: () => void): Promise<boolean> {
  const key = fnv1a(text.slice(0, 500));
  let blob = await cacheGet(key);
  if (!blob) {
    blob = await serverTts(text);
    if (!blob) {
      onDone?.();
      return false;
    }
    void cachePut(key, blob);
  }
  h5StopSpeak();
  try {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.playbackRate = readStoredSpeechRate();
    if (onDone) {
      audio.onended = () => onDone();
      audio.onerror = () => onDone();
    }
    currentObjectUrl = url;
    currentAudio = audio;
    await audio.play();
    return true;
  } catch {
    // 自动播放拦截等——明说而非静默
    showTtsToast("点击页面后重试朗读（浏览器自动播放策略）");
    onDone?.();
    return false;
  }
}

/**
 * 统一朗读入口。
 * - auto：浏览器有中文音色 → 浏览器；否则服务端（服务端失败回落浏览器尝试）。
 * - browser：仅浏览器。
 * - server：服务端优先，失败回落浏览器。
 */
export async function h5Speak(
  text: string,
  opts?: { onDone?: () => void; engine?: H5TtsEngine },
): Promise<void> {
  const clean = (text || "").trim();
  if (!clean) {
    opts?.onDone?.();
    return;
  }
  const engine = opts?.engine ?? readStoredTtsEngine();
  if (engine === "browser") {
    const ok = speakBrowser(clean, opts?.onDone);
    if (!ok && !hasChineseVoiceSync()) {
      showTtsToast("此浏览器无中文语音，可在「我的」切到服务端朗读");
    }
    return;
  }
  if (engine === "server") {
    const ok = await speakServer(clean, opts?.onDone);
    if (!ok) speakBrowser(clean, opts?.onDone);
    return;
  }
  // auto
  if (hasChineseVoiceSync()) {
    speakBrowser(clean, opts?.onDone);
    return;
  }
  const ok = await speakServer(clean, opts?.onDone);
  if (!ok) speakBrowser(clean, opts?.onDone);
}
