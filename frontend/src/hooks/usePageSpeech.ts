"use client";

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
import { serverTtsToBlob } from "../lib/h5-tts";

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

  // R#11（R3批/批⑥）：代际守卫位——stop() 不改 indexRef，在途 TTS fetch（0.5-2s）
  // 返回时旧守卫（index+engine）仍通过，会把已停止的段"复活"播放
  const epochRef = useRef(0);
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
      const myEpoch = epochRef.current;
      try {
        const blob = await serverTtsToBlob(list[idx].text, uRef.current);
        // 播放期间用户可能已 stop / seek：索引不符或代际已推进则丢弃本次结果（R#11）
        if (indexRef.current !== idx || engineRef.current !== "server" || epochRef.current !== myEpoch) return;
        const url = URL.createObjectURL(blob);
        audio.src = url;
        audio.onended = () => {
          URL.revokeObjectURL(url);
          const next = indexRef.current + 1;
          if (next < segmentsRef.current.length) {
            void speakFromServer(next);
          } else {
            setState("idle");
          }
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
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
    u.onend = () => {
      const next = indexRef.current + 1;
      if (next < list.length) {
        speakFromBrowser(next);
      } else {
        setState("idle");
      }
    };
    u.onerror = () => {
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
