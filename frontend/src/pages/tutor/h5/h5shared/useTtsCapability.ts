/**
 * T1（第十二篇）：朗读能力检测——把「静默失败」变成「明说」。
 * 原仓 hooks/useTtsCapability.ts 1:1 移植（仅 me 页消费的组内私有依赖，随组移植；
 * 删除 "use client"，SSR typeof window 守卫原样保留）。
 *
 * - 监听 voiceschanged（Chrome 异步加载语音）+ 挂载时首查 getVoices()；
 * - 三态：ok（有 zh 音色）/ no-voice（API 在但无中文音色）/ unsupported（无 speechSynthesis）；
 * - 另有 checking 过渡态（voices 可能异步到齐）。
 *
 * 搭配原仓 `web/lib/h5-tts.ts` 的 h5Speak 使用：no-voice 时自动落服务端合成。
 */

import { useEffect, useState } from "react";

export type TtsStatus = "checking" | "ok" | "no-voice" | "unsupported";

export interface TtsCapability {
  status: TtsStatus;
  /** 检测到的中文音色名（如「Microsoft 晓晓」），无则空串 */
  voiceName: string;
}

export function ttsEngineLabel(eng: "auto" | "browser" | "server"): string {
  if (eng === "browser") return "🔊 仅浏览器";
  if (eng === "server") return "☁️ 服务端优先";
  return "🪄 智能（浏览器优先）";
}

function detectChineseVoice(): { status: TtsStatus; voiceName: string } {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    return { status: "unsupported", voiceName: "" };
  }
  try {
    const voices = window.speechSynthesis.getVoices() || [];
    const zh = voices.filter((v) => (v.lang || "").toLowerCase().startsWith("zh"));
    if (zh.length === 0) return { status: "no-voice", voiceName: "" };
    // 优先普通话（cmn / zh-cn），其次任意 zh 音色
    const preferred =
      zh.find((v) => (v.lang || "").toLowerCase().includes("cmn")) ||
      zh.find((v) => (v.lang || "").toLowerCase().includes("zh-cn")) ||
      zh[0];
    return { status: "ok", voiceName: preferred?.name || zh[0]?.name || "" };
  } catch {
    return { status: "no-voice", voiceName: "" };
  }
}

export function useTtsCapability(): TtsCapability {
  const [cap, setCap] = useState<TtsCapability>(() => {
    // SSR 首渲染固定 checking，避免 hydration 不匹配
    if (typeof window === "undefined") return { status: "checking", voiceName: "" };
    const d = detectChineseVoice();
    // 首查即 unsupported 立即定论；no-voice 可能是 voices 未到齐，保持 checking 等 voiceschanged
    if (d.status === "unsupported") return d;
    if (d.status === "ok") return d;
    return { status: "checking", voiceName: "" };
  });

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setCap({ status: "unsupported", voiceName: "" });
      return;
    }
    const sync = () => {
      const d = detectChineseVoice();
      setCap(d);
    };
    sync();
    // Chrome 首查常为空，voiceschanged 到齐后再定论
    window.speechSynthesis.addEventListener("voiceschanged", sync);
    // 兜底：部分浏览器不触发 voiceschanged，短暂延迟后复查一次
    const t = setTimeout(sync, 600);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", sync);
      clearTimeout(t);
    };
  }, []);

  return cap;
}
