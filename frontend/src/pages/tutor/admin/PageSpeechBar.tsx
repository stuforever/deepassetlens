/**
 * ── 复刻来源与替换点（tupu antd 复刻）─────────────────────────────────
 * 源文件：DeepTutor web/app/(workspace)/book/components/PageSpeechBar.tsx
 * 目标：frontend/src/pages/tutor/admin/PageSpeechBar.tsx
 * 悬浮朗读控制条（播放/暂停/上下段/停止 + 分段进度条），布局/交互/文案 1:1。
 * 替换点：
 * - "use client" 已删除；
 * - react-i18next → 中文直出（原 t("中文", "English") 的中文 key 即文案原样）；
 * - lucide-react → @ant-design/icons 语义就近：
 *   Loader2→LoadingOutlined(spin)、Pause→PauseOutlined、Play→CaretRightOutlined、
 *   SkipBack→StepBackwardOutlined、SkipForward→StepForwardOutlined、
 *   Square→BorderOutlined、Volume2→SoundOutlined、X→CloseOutlined；
 *   h-3.5 w-3.5 → fontSize:14、h-4 w-4 → 16；
 * - `<input type="range">` → antd Slider（antd 自带已播进度轨道，
 *   原用于 backgroundSize 渐变的 percent 变量随之省略）；
 * - "@/hooks/usePageSpeech" → "./usePageSpeech"；
 * - Tailwind → 最小内联样式（border→#e4e4e7、muted-foreground→#6b7280、
 *   foreground→rgba(0,0,0,0.88)、primary→#1677ff、emerald→#10b981/#047857、
 *   amber→#f59e0b/#b45309、rounded-lg→8、2xl→12、full→999）。
 * - 保留差异：按钮 hover 配色（hover:bg-rose-100 等）为 CSS 伪类，内联样式
 *   无法表达，已省略；playing 圆点原带 animate-pulse 动画同此省略。
 * 导出形式（default PageSpeechBar + PageSpeechBarProps）与 props 契约不变。
 * ─────────────────────────────────────────────────────────────────────
 */

import { Button, Slider } from "antd";
import {
  BorderOutlined,
  CaretRightOutlined,
  CloseOutlined,
  LoadingOutlined,
  PauseOutlined,
  SoundOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
} from "@ant-design/icons";
import type { PageSpeech } from "./usePageSpeech";

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
      <div
        style={{
          borderRadius: 8,
          border: "1px solid #e4e4e7",
          background: "#fff",
          padding: "8px 12px",
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        当前浏览器不支持语音朗读
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <div
        style={{
          borderRadius: 8,
          border: "1px solid #e4e4e7",
          background: "#fff",
          padding: "8px 12px",
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        本页没有可朗读的文字内容
      </div>
    );
  }

  const playing = state === "speaking";
  const paused = state === "paused";
  const active = playing || paused;

  return (
    <div
      style={{
        overflow: "hidden",
        borderRadius: 12,
        border: "1px solid #e4e4e7",
        background: "#fff",
        boxShadow:
          "0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)",
      }}
    >
      {/* 标题栏 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          borderBottom: "1px solid #e4e4e7",
          background: "rgba(255,255,255,0.6)",
          padding: "8px 12px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            fontWeight: 500,
            color: "rgba(0,0,0,0.88)",
          }}
        >
          <SoundOutlined style={{ fontSize: 14, color: "#1677ff" }} />
          朗读
          {active && (
            <span
              style={{
                marginLeft: 4,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                borderRadius: 999,
                padding: "2px 8px",
                fontSize: 10,
                fontWeight: 600,
                background: playing
                  ? "rgba(16,185,129,0.15)"
                  : "rgba(245,158,11,0.15)",
                color: playing ? "#047857" : "#b45309",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: 999,
                  background: playing ? "#10b981" : "#f59e0b",
                }}
              />
              {playing ? "朗读中" : "已暂停"}
            </span>
          )}
        </div>
        {onClose && (
          <Button
            type="text"
            size="small"
            onClick={onClose}
            title="关闭朗读"
            icon={<CloseOutlined style={{ fontSize: 14 }} />}
            style={{
              width: 24,
              height: 24,
              minWidth: 24,
              padding: 0,
              borderRadius: 6,
              color: "#6b7280",
            }}
          />
        )}
      </div>

      {/* 控制区 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 12px",
        }}
      >
        <Button
          type="text"
          onClick={prev}
          disabled={!active || currentIndex <= 0}
          title="上一段"
          icon={<StepBackwardOutlined style={{ fontSize: 14 }} />}
          style={{
            width: 28,
            height: 28,
            minWidth: 28,
            padding: 0,
            borderRadius: 6,
            color: "rgba(0,0,0,0.88)",
          }}
        />
        <Button
          type="primary"
          shape="circle"
          onClick={toggle}
          title={active ? "暂停/继续" : "开始朗读"}
          icon={
            paused ? (
              <CaretRightOutlined style={{ fontSize: 16 }} />
            ) : playing ? (
              <PauseOutlined style={{ fontSize: 16 }} />
            ) : (
              <LoadingOutlined spin style={{ fontSize: 16 }} />
            )
          }
          style={{ width: 36, height: 36, minWidth: 36, padding: 0 }}
        />
        <Button
          type="text"
          onClick={next}
          disabled={!active || currentIndex >= segments.length - 1}
          title="下一段（快进）"
          icon={<StepForwardOutlined style={{ fontSize: 14 }} />}
          style={{
            width: 28,
            height: 28,
            minWidth: 28,
            padding: 0,
            borderRadius: 6,
            color: "rgba(0,0,0,0.88)",
          }}
        />
        <Button
          type="text"
          onClick={stop}
          disabled={!active}
          title="停止"
          icon={<BorderOutlined style={{ fontSize: 14 }} />}
          style={{
            width: 28,
            height: 28,
            minWidth: 28,
            padding: 0,
            borderRadius: 6,
            color: "rgba(0,0,0,0.88)",
          }}
        />

        <div
          style={{
            display: "flex",
            minWidth: 0,
            flex: 1,
            alignItems: "center",
            gap: 8,
          }}
        >
          <span
            title="拖动跳转段落"
            style={{ display: "flex", flex: 1, minWidth: 0 }}
          >
            <Slider
              min={0}
              max={segments.length - 1}
              step={1}
              value={Math.min(currentIndex, segments.length - 1)}
              disabled={segments.length <= 1}
              onChange={(v) => seek(Number(v))}
              tooltip={{ open: false }}
              style={{ flex: 1, minWidth: 0, margin: "0" }}
            />
          </span>
          <span
            style={{
              flexShrink: 0,
              fontSize: 11,
              fontVariantNumeric: "tabular-nums",
              color: "#6b7280",
            }}
          >
            {currentIndex + 1}/{segments.length}
          </span>
        </div>
      </div>
    </div>
  );
}
