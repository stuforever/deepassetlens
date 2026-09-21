/**
 * ── 复刻来源与替换点（tupu antd 复刻）─────────────────────────────────
 * 源文件：DeepTutor web/hooks/usePageSpeech.ts
 * 目标：frontend/src/pages/tutor/admin/usePageSpeech.ts
 * 浏览器 TTS hook——Web Speech API 逻辑原样保留（逐段播放/暂停/跳段/进度拖动），
 * 服务端合成降级（POST /api/v1/voice/tts → blob → <audio> 顺序播放）同样保留。
 * 替换点：
 * - "use client" 已删除（tupu 为 CRA/SPA，无 RSC）；
 * - `import { serverTtsToBlob } from "@/lib/h5-tts"`：tupu 无 h5-tts/h5-utils 基建，
 *   将 h5-tts.ts 中的 serverTtsToBlob 等价内联为本文件局部函数；
 *   其中 apiUrl(...) → fetch('/api/v1/...')（tupu 由 setupProxy 转发后端 28000）；
 *   getH5User() → tupu 无 H5 用户上下文，改为仅使用显式传入的 u（缺省空串，
 *   与原仓 PageReader 调用 usePageSpeech(segments) 不传 u 的行为一致）；
 *   「400 未配 TTS → toast」提示逻辑在 h5-tts 的 serverTts（带 toast 版）中，
 *   本 hook 用的本来就是静默版 serverTtsToBlob，故无 toast 逻辑需要迁移。
 * 其余类型导出（SpeechState/Segment/PageSpeech）与 hook 签名、引擎回退逻辑逐字保留。
 * ─────────────────────────────────────────────────────────────────────
 */

/**
 * Segment-level page speech control built on the browser Web Speech API.
 *
 * Web Speech (`speechSynthesis`) does not expose per-millisecond seeking, so
 * "scrubbing" here is segment-granular: the page is split into text segments
 * (one per readable block), and the user can play / pause / resume / stop,
 * skip to the next segment (fast-forward) or drag the progress bar to jump
 * straight to any segment.  Segments play back-to-back automatically.
 *
 * 第十二篇 T2（引擎适配）：浏览器无中文语音时自动降级到服务端合成
 * （POST /api/v1/voice/tts → blob → <audio> 顺序播放），对页面保持原 API。
 * 服务端合成失败（未配置 400）时回落浏览器引擎逐段朗读。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type SpeechState = "idle" | "speaking" | "paused" | "unsupported";

export interface Segment {
  id: string;
  text: string;
}

export interface PageSpeech {
  /** Voice-ready text segments (non-empty, whitespace-trimmed). */
  segments: Segment[];
  /** Play / pause / continue / stop. */
  toggle(): void;
  pause(): void;
  resume(): void;
  stop(): void;
  /** Jump to a segment (drag on the progress bar). */
  seek(index: number): void;
  /** Skip forward one segment (fast-forward). */
  next(): void;
  /** Go back one segment. */
  prev(): void;
  state: SpeechState;
  currentIndex: number;
  supported: boolean;
  /** 当前引擎（调试/展示用） */
  engine: "browser" | "server" | "none";
}

/**
 * 内联自 h5-tts.ts 的静默版服务端合成（供段播用）：不弹 toast（段播失败会自动回落浏览器）。
 * 显式传 u（hook 不在 h5 用户上下文里时也能隔离）。
 */
async function serverTtsToBlob(text: string, explicitU?: string): Promise<Blob> {
  const u = explicitU || "";
  const qs = u ? `?u=${encodeURIComponent(u)}` : "";
  const res = await fetch(`/api/v1/voice/tts${qs}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text.slice(0, 2000) }),
  });
  if (!res.ok) {
    throw new Error(`tts ${res.status}`);
  }
  return await res.blob();
}

function pickChineseVoice(): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  const zh = voices.filter((v) => v.lang.toLowerCase().startsWith("zh"));
  if (zh.length === 0) return null;
  // Prefer a Mandarin voice, then any zh voice (stable order sort).
  const mandarin = zh.find((v) => v.lang.toLowerCase().includes("cmn"));
  const chinese = zh.find((v) => v.lang.toLowerCase().includes("zh-cn"));
  return mandarin || chinese || zh[0];
}

export function usePageSpeech(
  segments: Segment[],
  opts?: { u?: string },
): PageSpeech {
  const [state, setState] = useState<SpeechState>(
    () =>
      typeof window !== "undefined" && window.speechSynthesis ? "idle" : "unsupported",
  );
  const [currentIndex, setCurrentIndex] = useState(0);
  const [engine, setEngine] = useState<"browser" | "server" | "none">("none");

  const segmentsRef = useRef(segments);
  const indexRef = useRef(0);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const boundaryRef = useRef<SpeechSynthesisUtterance | null>(null);
  // 服务端引擎：<audio> 顺序播放；engineRef 在首次播放时定格
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const engineRef = useRef<"browser" | "server" | "none">("none");
  // R0 重放批：代际守卫——synth.cancel() 会触发 onend/onerror，无守卫则 stop 后旧链
  // 继续推进下一段（竞态；同 E-79 h5-tts speakEpoch 同族修法）
  const epochRef = useRef(0);
  const uRef = useRef(opts?.u || "");

  useEffect(() => {
    uRef.current = opts?.u || "";
  }, [opts?.u]);

  useEffect(() => {
    segmentsRef.current = segments;
    if (indexRef.current >= segments.length) indexRef.current = 0;
    setCurrentIndex(indexRef.current);
    stopAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments]);

  // Keep a voice handle ready (voices load async).
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    const sync = () => {
      voiceRef.current = pickChineseVoice();
      if (engineRef.current === "none") {
        const eng = voiceRef.current ? "browser" : "server";
        engineRef.current = eng;
        setEngine(eng);
      }
    };
    sync();
    window.speechSynthesis.addEventListener("voiceschanged", sync);
    return () =>
      window.speechSynthesis.removeEventListener("voiceschanged", sync);
  }, []);

  const stopAll = useCallback(() => {
    epochRef.current += 1;
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (audioRef.current) {
      try {
        audioRef.current.pause();
      } catch {
        /* ignore */
      }
    }
  }, []);

  const getAudio = useCallback(() => {
    if (!audioRef.current && typeof window !== "undefined") {
      audioRef.current = new Audio();
    }
    return audioRef.current!;
  }, []);

  /** 服务端引擎：逐段取 blob 播放（失败回落浏览器） */
  const speakFromServer = useCallback(
    async (startIndex: number) => {
      const list = segmentsRef.current;
      if (list.length === 0) return;
      const idx = Math.max(0, Math.min(startIndex, list.length - 1));
      indexRef.current = idx;
      setCurrentIndex(idx);
      const audio = getAudio();
      setState("speaking");
      try {
        const blob = await serverTtsToBlob(list[idx].text, uRef.current);
        // 播放期间用户可能已 stop / seek：索引不符则丢弃本次结果
        if (indexRef.current !== idx || engineRef.current !== "server") return;
        const url = URL.createObjectURL(blob);
        const myEpoch = epochRef.current;
        audio.src = url;
        audio.onended = () => {
          URL.revokeObjectURL(url);
          if (epochRef.current !== myEpoch) return;
          const next = indexRef.current + 1;
          if (next < segmentsRef.current.length) {
            void speakFromServer(next);
          } else {
            setState("idle");
          }
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          if (epochRef.current !== myEpoch) return;
          // 服务端音频坏了 → 本段回落浏览器
          engineRef.current = "browser";
          setEngine("browser");
          speakFromBrowser(idx);
        };
        await audio.play();
      } catch {
        // 服务端未配置/网络失败 → 整体回落浏览器引擎
        engineRef.current = "browser";
        setEngine("browser");
        speakFromBrowser(idx);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [getAudio],
  );

  /** 浏览器引擎：原逐段 speechSynthesis 播放 */
  const speakFromBrowser = useCallback((startIndex: number) => {
    const synth = window.speechSynthesis;
    if (!synth) return;
    const list = segmentsRef.current;
    if (list.length === 0) return;
    const idx = Math.max(0, Math.min(startIndex, list.length - 1));
    indexRef.current = idx;
    setCurrentIndex(idx);
    const u = new SpeechSynthesisUtterance(list[idx].text);
    if (voiceRef.current) u.voice = voiceRef.current;
    u.lang = voiceRef.current?.lang || "zh-CN";
    u.rate = 1.0;
    boundaryRef.current = u;
    const myEpoch = epochRef.current;
    u.onend = () => {
      if (epochRef.current !== myEpoch) return;
      const next = indexRef.current + 1;
      if (next < list.length) {
        speakFromBrowser(next);
      } else {
        setState("idle");
      }
    };
    u.onerror = () => {
      if (epochRef.current !== myEpoch) return;
      if (synth.paused) return;
      const next = indexRef.current + 1;
      if (next < list.length) {
        speakFromBrowser(next);
      } else {
        setState("idle");
      }
    };
    setState("speaking");
    synth.speak(u);
  }, []);

  const speakFrom = useCallback(
    (startIndex: number) => {
      stopAll();
      if (engineRef.current === "server") {
        void speakFromServer(startIndex);
      } else {
        speakFromBrowser(startIndex);
      }
    },
    [stopAll, speakFromServer, speakFromBrowser],
  );

  const stop = useCallback(() => {
    stopAll();
    indexRef.current = Math.max(0, indexRef.current);
    setState("idle");
  }, [stopAll]);

  const pause = useCallback(() => {
    if (engineRef.current === "server") {
      const audio = getAudio();
      if (!audio.paused) {
        audio.pause();
        setState("paused");
      }
      return;
    }
    const synth = window.speechSynthesis;
    if (!synth || !synth.speaking) return;
    synth.pause();
    setState("paused");
  }, [getAudio]);

  const resume = useCallback(() => {
    if (engineRef.current === "server") {
      const audio = getAudio();
      if (audio.paused && audio.src) {
        void audio.play();
        setState("speaking");
        return;
      }
      speakFrom(indexRef.current);
      return;
    }
    const synth = window.speechSynthesis;
    if (!synth) return;
    if (synth.paused) {
      synth.resume();
      setState("speaking");
      return;
    }
    // Start (or restart from a segment) when idle.
    speakFrom(indexRef.current);
  }, [speakFrom, getAudio]);

  const toggle = useCallback(() => {
    if (engineRef.current === "server") {
      const audio = getAudio();
      if (!audio.paused && audio.src && state === "speaking") {
        pause();
      } else if (audio.paused && audio.src && state === "paused") {
        resume();
      } else {
        speakFrom(indexRef.current);
      }
      return;
    }
    const synth = window.speechSynthesis;
    if (!synth) return;
    if (synth.speaking && !synth.paused) {
      pause();
    } else if (synth.paused) {
      resume();
    } else {
      speakFrom(indexRef.current);
    }
  }, [pause, resume, speakFrom, state, getAudio]);

  const next = useCallback(() => {
    speakFrom(indexRef.current + 1);
  }, [speakFrom]);

  const prev = useCallback(() => {
    speakFrom(indexRef.current - 1);
  }, [speakFrom]);

  const seek = useCallback(
    (index: number) => {
      speakFrom(index);
    },
    [speakFrom],
  );

  const supported = typeof window !== "undefined" && (!!window.speechSynthesis || true);

  // 卸载时清理双通道
  useEffect(() => {
    return () => {
      stopAll();
    };
  }, [stopAll]);

  return useMemo(
    () => ({
      segments,
      toggle,
      pause,
      resume,
      stop,
      seek,
      next,
      prev,
      state,
      currentIndex,
      supported,
      engine,
    }),
    [segments, toggle, pause, resume, stop, seek, next, prev, state, currentIndex, supported, engine],
  );
}
