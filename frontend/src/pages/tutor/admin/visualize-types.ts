/**
 * 1:1 复刻自 DeepTutor web/lib/visualize-types.ts（tupu 批8 book 页依赖）。
 * 替换点：
 * 1) 原对 math-animator-types 的导入按使用面整体内联到本文件尾部
 *    （MathAnimatorOutputMode / MathAnimatorArtifact / MathAnimatorResult /
 *    extractMathAnimatorResult，定义逐字保留、不对外导出，导出面与原
 *    visualize-types.ts 完全一致）；
 * 2) 仅新增本文件头注释；
 * 其余类型、常量、函数与导出名逐字保留，未裁剪。
 */

export type VisualizeTextRenderType = "svg" | "chartjs" | "mermaid" | "html";
export type VisualizeManimRenderType = "manim_video" | "manim_image";
export type VisualizeRenderType =
  | VisualizeTextRenderType
  | VisualizeManimRenderType;
export type VisualizeRenderMode = "auto" | VisualizeRenderType;

export interface VisualizeFormConfig {
  render_mode: VisualizeRenderMode;
  // Only consumed by the backend when the resolved render_type ends up
  // being manim_video / manim_image. Ignored on text-only paths but kept
  // in form state so toggling between modes preserves the user's choice.
  quality: "low" | "medium" | "high";
  style_hint: string;
}

export const DEFAULT_VISUALIZE_CONFIG: VisualizeFormConfig = {
  render_mode: "auto",
  quality: "medium",
  style_hint: "",
};

export function buildVisualizeWSConfig(
  cfg: VisualizeFormConfig,
): Record<string, unknown> {
  return {
    render_mode: cfg.render_mode,
    quality: cfg.quality,
    style_hint: cfg.style_hint.trim(),
  };
}

const VISUALIZE_RENDER_LABELS: Record<VisualizeRenderMode, string> = {
  auto: "Auto",
  chartjs: "Chart.js",
  svg: "SVG",
  mermaid: "Mermaid",
  html: "HTML",
  manim_video: "Animation",
  manim_image: "Storyboard",
};

export function isManimRenderType(
  renderType: string,
): renderType is VisualizeManimRenderType {
  return renderType === "manim_video" || renderType === "manim_image";
}

export function isManimResult(
  result: VisualizeResult,
): result is VisualizeManimResult {
  return isManimRenderType(result.render_type);
}

/**
 * One-line summary of the visualize form, shown next to the collapsed
 * `Settings` chevron in the composer. Pass `translate` (typically the
 * `t` function from the caller's i18n layer) so the summary follows the
 * active UI language.
 */
export function summarizeVisualizeConfig(
  cfg: VisualizeFormConfig,
  translate?: (key: string) => string,
): string {
  const label = VISUALIZE_RENDER_LABELS[cfg.render_mode] ?? cfg.render_mode;
  const text = translate ? translate(label) : label;
  // For manim modes, surface the quality tier alongside the format —
  // matches what users were used to in the old Animator panel.
  if (cfg.render_mode === "manim_video" || cfg.render_mode === "manim_image") {
    const qLabel = cfg.quality.charAt(0).toUpperCase() + cfg.quality.slice(1);
    const q = translate ? translate(qLabel) : qLabel;
    return `${text} · ${q}`;
  }
  return text;
}

interface VisualizeTextResult {
  response: string;
  render_type: VisualizeTextRenderType;
  code: {
    language: string;
    content: string;
  };
  analysis: {
    render_type: string;
    description: string;
    data_description: string;
    chart_type: string;
    visual_elements: string[];
    rationale: string;
  };
  review: {
    optimized_code: string;
    changed: boolean;
    review_notes: string;
  };
}

interface VisualizeManimResult {
  render_type: VisualizeManimRenderType;
  manim: MathAnimatorResult;
}

export type VisualizeResult = VisualizeTextResult | VisualizeManimResult;

export function extractVisualizeResult(
  resultMetadata: Record<string, unknown> | undefined,
): VisualizeResult | null {
  if (!resultMetadata) return null;

  const renderType = resultMetadata.render_type;

  // Manim path: delegate decoding to math-animator-types so the existing
  // MathAnimatorViewer can render the artefacts unchanged.
  if (renderType === "manim_video" || renderType === "manim_image") {
    const manim = extractMathAnimatorResult(resultMetadata);
    if (!manim) return null;
    return { render_type: renderType, manim };
  }

  if (
    renderType !== "svg" &&
    renderType !== "chartjs" &&
    renderType !== "mermaid" &&
    renderType !== "html"
  )
    return null;

  const codeRaw =
    resultMetadata.code && typeof resultMetadata.code === "object"
      ? (resultMetadata.code as Record<string, unknown>)
      : {};

  if (!codeRaw.content) return null;

  return {
    response: String(resultMetadata.response ?? ""),
    render_type: renderType,
    code: {
      language: String(codeRaw.language ?? ""),
      content: String(codeRaw.content ?? ""),
    },
    analysis:
      resultMetadata.analysis && typeof resultMetadata.analysis === "object"
        ? (resultMetadata.analysis as VisualizeTextResult["analysis"])
        : {
            render_type: renderType,
            description: "",
            data_description: "",
            chart_type: "",
            visual_elements: [],
            rationale: "",
          },
    review:
      resultMetadata.review && typeof resultMetadata.review === "object"
        ? (resultMetadata.review as VisualizeTextResult["review"])
        : { optimized_code: "", changed: false, review_notes: "" },
  };
}

// ---- 以下为按使用面内联自 DeepTutor web/lib/math-animator-types.ts 的符号
// ---- （该文件全部导出即这 4 个，定义逐字保留；不重复导出，导出面保持与
// ---- 原 visualize-types.ts 一致）。

type MathAnimatorOutputMode = "video" | "image";

interface MathAnimatorArtifact {
  type: "video" | "image";
  url: string;
  filename: string;
  content_type?: string;
  label?: string;
}

interface MathAnimatorResult {
  response: string;
  output_mode: MathAnimatorOutputMode;
  code: {
    language: string;
    content: string;
  };
  artifacts: MathAnimatorArtifact[];
  timings: Record<string, number>;
  render: {
    quality?: string;
    retry_attempts?: number;
    retry_history?: Array<{ attempt: number; error: string }>;
    source_code_path?: string;
    visual_review?: {
      passed?: boolean;
      summary?: string;
      issues?: string[];
      suggested_fix?: string;
      reviewed_frames?: number;
    } | null;
  };
  summary?: {
    summary_text?: string;
    user_request?: string;
    generated_output?: string;
    key_points?: string[];
  };
}

function extractMathAnimatorResult(
  resultMetadata: Record<string, unknown> | undefined,
): MathAnimatorResult | null {
  if (!resultMetadata) return null;
  const artifacts = Array.isArray(resultMetadata.artifacts)
    ? resultMetadata.artifacts.filter((item): item is MathAnimatorArtifact => {
        return Boolean(
          item &&
          typeof item === "object" &&
          "type" in item &&
          "url" in item &&
          "filename" in item,
        );
      })
    : [];
  const codeRaw =
    resultMetadata.code && typeof resultMetadata.code === "object"
      ? (resultMetadata.code as Record<string, unknown>)
      : {};
  const hasOutputMode =
    resultMetadata.output_mode === "image" ||
    resultMetadata.output_mode === "video";
  const timings =
    resultMetadata.timings && typeof resultMetadata.timings === "object"
      ? (resultMetadata.timings as Record<string, number>)
      : {};
  const render =
    resultMetadata.render && typeof resultMetadata.render === "object"
      ? (resultMetadata.render as MathAnimatorResult["render"])
      : {};
  const outputMode = resultMetadata.output_mode === "image" ? "image" : "video";

  // A plain `response` field is common across capabilities. Only treat the
  // payload as a math-animator result when it carries math-animator-specific
  // artifacts or render metadata.
  if (
    !artifacts.length &&
    !codeRaw.content &&
    !hasOutputMode &&
    Object.keys(timings).length === 0 &&
    Object.keys(render).length === 0
  ) {
    return null;
  }

  return {
    response: String(resultMetadata.response ?? ""),
    output_mode: outputMode,
    code: {
      language: String(codeRaw.language ?? "python"),
      content: String(codeRaw.content ?? ""),
    },
    artifacts,
    timings,
    render,
    summary:
      resultMetadata.summary && typeof resultMetadata.summary === "object"
        ? (resultMetadata.summary as MathAnimatorResult["summary"])
        : undefined,
  };
}
