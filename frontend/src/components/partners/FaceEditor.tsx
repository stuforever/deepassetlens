/**
 * 复刻自 DeepTutor 原仓 web/components/partners/FaceEditor.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover/scale 用 onMouseEnter/onMouseLeave 事件直写，本仓既定口径；
 * 响应式断点直接取桌面值）；FaceEditor 传给 PartnerAvatar 的 className="shadow-sm"
 * 按源保留透传（无 tailwind 环境该类不生效，仅装饰性阴影差异，登记）。
 * lucide-react→antd 图标登记：ImagePlus → PictureOutlined；X → CloseOutlined。
 *
 * iOS-contacts-style face editor: a large live preview on top, then an emoji
 * grid, a background color row, and photo/SVG upload. Emoji + color compose
 * (the color is the disc behind the emoji); an uploaded image wins over both
 * and any emoji tap switches back to emoji mode.
 */

import { useRef, useState } from "react";
import { CloseOutlined, PictureOutlined } from "@ant-design/icons";
import PartnerAvatar, {
  PARTNER_COLORS,
} from "./PartnerAvatar";

const ZH_MESSAGES: Record<string, string> = {
  "Use a PNG, JPG, WebP, GIF, or SVG image.":
    "请使用 PNG、JPG、WebP、GIF 或 SVG 图片。",
  "That file is too large.": "文件太大了。",
  "Could not read that image.": "无法读取该图片。",
  "Replace photo": "更换图片",
  "Upload photo or SVG": "上传图片 / SVG",
  Remove: "移除",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

export const FACE_EMOJIS = [
  "🦊",
  "🐳",
  "🦉",
  "🐱",
  "🐶",
  "🐼",
  "🐨",
  "🦁",
  "🐯",
  "🐸",
  "🐙",
  "🦄",
  "🤖",
  "👾",
  "🌱",
  "🌸",
  "🍀",
  "🌙",
  "✨",
  "🔥",
  "📚",
  "🎨",
  "🎧",
  "🧭",
] as const;

export interface FaceValue {
  emoji: string;
  color: string;
  avatar: string; // data URL; "" = none
}

const AVATAR_SIZE = 128;
const SVG_MAX_BYTES = 100 * 1024;
const RASTER_MAX_BYTES = 10 * 1024 * 1024;

async function fileToAvatarDataUrl(file: File): Promise<string> {
  if (file.type === "image/svg+xml") {
    if (file.size > SVG_MAX_BYTES) {
      throw new Error("svg-too-large");
    }
    const text = await file.text();
    // Array.from 包装：本仓 tsconfig target 较低，直接展开 Uint8Array 需要
    // downlevelIteration（语义与源仓展开迭代逐字等价）。
    const base64 = btoa(
      String.fromCharCode(...Array.from(new TextEncoder().encode(text))),
    );
    return `data:image/svg+xml;base64,${base64}`;
  }
  if (!/^image\/(png|jpe?g|webp|gif)$/.test(file.type)) {
    throw new Error("unsupported-type");
  }
  if (file.size > RASTER_MAX_BYTES) {
    throw new Error("file-too-large");
  }
  // Center-crop to a square and downscale — avatars render at ≤56px, so
  // 128px keeps config payloads tiny without visible quality loss.
  const bitmap = await createImageBitmap(file);
  try {
    const side = Math.min(bitmap.width, bitmap.height);
    const sx = (bitmap.width - side) / 2;
    const sy = (bitmap.height - side) / 2;
    const canvas = document.createElement("canvas");
    canvas.width = AVATAR_SIZE;
    canvas.height = AVATAR_SIZE;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas-unavailable");
    ctx.drawImage(bitmap, sx, sy, side, side, 0, 0, AVATAR_SIZE, AVATAR_SIZE);
    const webp = canvas.toDataURL("image/webp", 0.9);
    return webp.startsWith("data:image/webp")
      ? webp
      : canvas.toDataURL("image/png");
  } finally {
    bitmap.close();
  }
}

export default function FaceEditor({
  name,
  value,
  onChange,
}: {
  name: string;
  value: FaceValue;
  onChange: (next: FaceValue) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [hoveredEmoji, setHoveredEmoji] = useState<number | null>(null);
  const [hoveredColor, setHoveredColor] = useState<string | null>(null);
  const [uploadHover, setUploadHover] = useState(false);
  const [removeHover, setRemoveHover] = useState(false);

  const hasImage = Boolean(value.avatar);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setUploadError("");
    try {
      const avatar = await fileToAvatarDataUrl(file);
      onChange({ ...value, avatar });
    } catch (e) {
      const code = e instanceof Error ? e.message : "";
      setUploadError(
        code === "unsupported-type"
          ? t("Use a PNG, JPG, WebP, GIF, or SVG image.")
          : code === "svg-too-large" || code === "file-too-large"
            ? t("That file is too large.")
            : t("Could not read that image."),
      );
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
      }}
    >
      {/* Live preview */}
      <PartnerAvatar
        name={name || "?"}
        emoji={value.emoji}
        color={value.color}
        image={value.avatar}
        size={88}
        className="shadow-sm"
      />

      {/* Emoji grid — tapping any emoji leaves image mode */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(8, minmax(0, 1fr))",
          gap: 6,
        }}
      >
        {FACE_EMOJIS.map((preset, index) => {
          const active = !hasImage && value.emoji === preset;
          return (
            <button
              key={preset}
              type="button"
              onClick={() =>
                onChange({
                  ...value,
                  avatar: "",
                  emoji: active ? "" : preset,
                })
              }
              onMouseEnter={() => setHoveredEmoji(index)}
              onMouseLeave={() => setHoveredEmoji(null)}
              style={{
                display: "flex",
                height: 36,
                width: 36,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 9999,
                fontSize: 17,
                lineHeight: 1,
                cursor: "pointer",
                border: `1px solid ${
                  active
                    ? "var(--primary, #2563eb)"
                    : hoveredEmoji === index
                      ? "var(--border, #e2e8f0)"
                      : "transparent"
                }`,
                background:
                  active || hoveredEmoji === index
                    ? active
                      ? "var(--secondary, #f1f5f9)"
                      : "var(--muted, #f1f5f9)"
                    : "transparent",
                transition: "background-color 150ms, border-color 150ms",
              }}
            >
              {preset}
            </button>
          );
        })}
      </div>

      {/* Background colors — the disc behind the emoji / initial */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          pointerEvents: hasImage ? "none" : "auto",
          opacity: hasImage ? 0.35 : 1,
        }}
        aria-disabled={hasImage}
      >
        {PARTNER_COLORS.map((preset) => (
          <button
            key={preset}
            type="button"
            aria-label={preset}
            onClick={() =>
              onChange({
                ...value,
                color: value.color === preset ? "" : preset,
              })
            }
            onMouseEnter={() => setHoveredColor(preset)}
            onMouseLeave={() => setHoveredColor(null)}
            style={{
              display: "flex",
              height: 24,
              width: 24,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 9999,
              border: "none",
              padding: 0,
              cursor: "pointer",
              background: preset,
              transform: hoveredColor === preset ? "scale(1.1)" : "scale(1)",
              transition: "transform 150ms",
            }}
          >
            {value.color === preset && (
              <span
                style={{
                  height: 8,
                  width: 8,
                  borderRadius: 9999,
                  background: "rgba(255, 255, 255, 0.9)",
                  display: "block",
                }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Upload / remove */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
          style={{ display: "none" }}
          onChange={(e) => {
            void handleFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          onMouseEnter={() => setUploadHover(true)}
          onMouseLeave={() => setUploadHover(false)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            borderRadius: 8,
            border: `1px solid ${
              uploadHover ? "var(--ring, #2563eb)" : "var(--border, #e2e8f0)"
            }`,
            padding: "6px 12px",
            fontSize: 13,
            fontWeight: 500,
            color: "var(--foreground, #0f172a)",
            background: "transparent",
            cursor: "pointer",
            transition: "border-color 150ms",
          }}
        >
          <PictureOutlined style={{ fontSize: 14 }} />
          {hasImage ? t("Replace photo") : t("Upload photo or SVG")}
        </button>
        {hasImage && (
          <button
            type="button"
            onClick={() => onChange({ ...value, avatar: "" })}
            onMouseEnter={() => setRemoveHover(true)}
            onMouseLeave={() => setRemoveHover(false)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              borderRadius: 8,
              border: "none",
              padding: "6px 10px",
              fontSize: 13,
              color:
                removeHover
                  ? "var(--foreground, #0f172a)"
                  : "var(--muted-foreground, #64748b)",
              background: "transparent",
              cursor: "pointer",
              transition: "color 150ms",
            }}
          >
            <CloseOutlined style={{ fontSize: 14 }} />
            {t("Remove")}
          </button>
        )}
      </div>
      {uploadError && (
        <p
          style={{
            fontSize: 12,
            color: "var(--destructive, #ef4444)",
            margin: 0,
          }}
        >
          {uploadError}
        </p>
      )}
    </div>
  );
}
