"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch, apiUrl } from "../lib/api";

export type RecorderState = "idle" | "recording" | "transcribing";

/**
 * Microphone capture → backend transcription. Records via MediaRecorder, posts
 * the clip to ``/api/v1/voice/stt`` (which uses the admin-configured STT
 * provider), and hands the transcript back through ``onTranscript``.
 */
export function useVoiceRecorder(onTranscript: (text: string) => void) {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  // 三轨M11 顺手修(:28)：重入竞态闸——state 要到 start() 末尾才更新，
  // getUserMedia await 期间二次调用会绕过守卫（双 MediaStream+麦克风泄漏）。
  // stateRef 同步读写，进入即置 "recording" 占位。
  const stateRef = useRef(state);
  // R5批⑥：删除渲染期无条件回写（原 stateRef.current = state）——await getUserMedia
  // 期间父组件重渲染会以滞后的渲染态（"idle"）冲掉 start() 置入的 "recording" 占位，
  // 重入闸被击穿（双 MediaStream+麦克风泄漏）。状态变更统一走同步双写包装器。
  const setStateRef = useCallback((next: RecorderState) => {
    stateRef.current = next;
    setState(next);
  }, []);
  const start = useCallback(async () => {
    if (stateRef.current !== "idle") return;
    stateRef.current = "recording"; // 同步占位（render state 随后跟上）
    setError(null);
    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError("Recording is not supported in this browser.");
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e: any) {
      // 三轨M11(:42)：错误分类——NotReadable/NotFound 等不再笼统报 permission denied
      stateRef.current = "idle"; // 失败回滚占位
      setError(
        e?.name === "NotFoundError" ? "未检测到麦克风设备。"
        : e?.name === "NotReadableError" ? "麦克风被其他应用占用。"
        : e?.name === "NotAllowedError" ? "麦克风权限被拒绝。"
        : "录音启动失败。",
      );
      return;
    }
    streamRef.current = stream;
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = async () => {
      const mimeType = recorder.mimeType || "audio/webm";
      releaseStream();
      const blob = new Blob(chunksRef.current, { type: mimeType });
      chunksRef.current = [];
      if (!blob.size) {
        setStateRef("idle");
        return;
      }
      setStateRef("transcribing");
      try {
        const ext = mimeType.includes("ogg")
          ? "ogg"
          : mimeType.includes("mp4")
            ? "mp4"
            : "webm";
        const form = new FormData();
        form.append("file", blob, `recording.${ext}`);
        const resp = await apiFetch(apiUrl("/api/v1/voice/stt"), {
          method: "POST",
          body: form,
        });
        if (!resp.ok) {
          const detail = (await resp.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(
            detail?.detail || `Transcription failed (HTTP ${resp.status}).`,
          );
        }
        const data = (await resp.json()) as { text?: string };
        const text = (data.text || "").trim();
        if (text) onTranscriptRef.current(text);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Transcription failed.");
      } finally {
        setStateRef("idle");
      }
    };
    recorder.start();
    recorderRef.current = recorder;
    setStateRef("recording");
  }, [releaseStream, state]);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop(); // fires onstop → transcribe
    }
  }, []);

  const toggle = useCallback(() => {
    if (state === "recording") stop();
    else if (state === "idle") void start();
  }, [start, state, stop]);

  // Stop the mic if the component unmounts mid-recording.
  // 三轨M11 顺手修(:110)：卸载后 onstop 回调（转写 POST/onTranscript/setState）一并拦截
  // ——用户离开页面不再上传录音。
  const unmountedRef = useRef(false);
  useEffect(() => {
    return () => {
      unmountedRef.current = true;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null; // 短路异步 onstop（卸载后不再转写上传）
        recorder.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  return { state, error, toggle, start, stop };
}
