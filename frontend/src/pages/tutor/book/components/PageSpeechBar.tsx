"use client";

import {
  Loader2,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  Square,
  Volume2,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { PageSpeech } from "../../../../hooks/usePageSpeech";

export interface PageSpeechBarProps {
  speech: PageSpeech;
  /** 关闭悬浮窗（停止朗读并收起）。 */
  onClose?: () => void;
}

/**
 * Floating speech control window for page read-aloud. Segment-granular:
 * play/pause/resume/stop, skip segment (fast-forward / back), and a progress
 * bar that jumps to any segment when dragged.
 */
export default function PageSpeechBar({ speech, onClose }: PageSpeechBarProps) {
  const { t } = useTranslation();
  const {
    segments,
    state,
    currentIndex,
    toggle,
    stop,
    next,
    prev,
    seek,
    supported,
  } = speech;

  if (!supported) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs text-[var(--muted-foreground)]">
        {t("当前浏览器不支持语音朗读", "Speech synthesis is not supported in this browser.")}
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs text-[var(--muted-foreground)]">
        {t("本页没有可朗读的文字内容", "This page has no readable text.")}
      </div>
    );
  }

  const playing = state === "speaking";
  const paused = state === "paused";
  const active = playing || paused;
  const percent =
    segments.length > 0 ? ((currentIndex + 1) / segments.length) * 100 : 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl">
      {/* 标题栏 */}
      <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--background)]/60 px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-medium text-[var(--foreground)]">
          <Volume2 className="h-3.5 w-3.5 text-[var(--primary)]" />
          {t("朗读", "Read aloud")}
          {active && (
            <span
              className={`ml-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                playing
                  ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                  : "bg-amber-500/15 text-amber-700 dark:text-amber-300"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  playing ? "animate-pulse bg-emerald-500" : "bg-amber-500"
                }`}
              />
              {playing ? t("朗读中", "Speaking") : t("已暂停", "Paused")}
            </span>
          )}
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            title={t("关闭朗读", "Close read-aloud")}
            className="inline-flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--background)] hover:text-[var(--foreground)]"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* 控制区 */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button
          type="button"
          onClick={prev}
          disabled={!active || currentIndex <= 0}
          title={t("上一段", "Previous segment")}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--foreground)] hover:bg-[var(--background)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SkipBack className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={toggle}
          title={
            active ? t("暂停/继续", "Pause / Resume") : t("开始朗读", "Read aloud")
          }
          className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[var(--primary)] text-primary-foreground hover:opacity-90"
        >
          {paused ? (
            <Play className="h-4 w-4" />
          ) : playing ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin" />
          )}
        </button>
        <button
          type="button"
          onClick={next}
          disabled={!active || currentIndex >= segments.length - 1}
          title={t("下一段（快进）", "Next segment (fast-forward)")}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--foreground)] hover:bg-[var(--background)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SkipForward className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={stop}
          disabled={!active}
          title={t("停止", "Stop")}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--foreground)] hover:bg-rose-100 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-rose-500/10 dark:hover:text-rose-200"
        >
          <Square className="h-3.5 w-3.5" />
        </button>

        <div className="flex min-w-0 flex-1 items-center gap-2">
          <input
            type="range"
            min={0}
            max={segments.length - 1}
            step={1}
            value={Math.min(currentIndex, segments.length - 1)}
            disabled={segments.length <= 1}
            onChange={(e) => seek(Number(e.target.value))}
            className="h-1.5 min-w-0 flex-1 cursor-pointer accent-[var(--primary)] disabled:cursor-default"
            style={{ backgroundSize: `${percent}% 100%` }}
            title={t("拖动跳转段落", "Drag to jump segments")}
          />
          <span className="shrink-0 text-[11px] tabular-nums text-[var(--muted-foreground)]">
            {currentIndex + 1}/{segments.length}
          </span>
        </div>
      </div>
    </div>
  );
}
