import { Select as AntSelect } from "antd";
"use client";

import { memo } from "react";
import { useTranslation } from "react-i18next";
import {
  summarizeVisualizeConfig,
  type VisualizeFormConfig,
} from "../../lib/visualize-types";
import {
  CollapsibleConfigSection,
  Field,
  INPUT_CLS,
} from "../chat/home/composer-field";

interface VisualizeConfigPanelProps {
  value: VisualizeFormConfig;
  onChange: (next: VisualizeFormConfig) => void;
  /**
   * When provided, the panel is wrapped in a `CollapsibleConfigSection`.
   * Omit both to render bare for the chat Activity panel.
   */
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

export default memo(function VisualizeConfigPanel({
  value,
  onChange,
  collapsed,
  onToggleCollapsed,
}: VisualizeConfigPanelProps) {
  const { t } = useTranslation();
  const update = <K extends keyof VisualizeFormConfig>(
    key: K,
    val: VisualizeFormConfig[K],
  ) => onChange({ ...value, [key]: val });

  // Manim modes need extra knobs (render quality, style hint) — match what
  // the legacy Animator panel exposed so users don't lose granularity when
  // they pick "Animation" / "Storyboard" here.
  const isManim =
    value.render_mode === "manim_video" || value.render_mode === "manim_image";

  const body = (
    <>
      <Field label={t("Render Mode")} width="w-[140px]">
        <AntSelect
          value={value.render_mode}
          onChange={(v) => update("render_mode", v as VisualizeFormConfig["render_mode"])}
          size="small"
          style={{ width: "100%" }}
          options={[
            { value: "auto", label: t("Auto") },
            { value: "chartjs", label: t("Chart.js") },
            { value: "svg", label: t("SVG") },
            { value: "mermaid", label: t("Mermaid") },
            { value: "html", label: t("HTML") },
            { value: "manim_video", label: t("Animation") },
            { value: "manim_image", label: t("Storyboard") },
          ]}
        />
      </Field>

      {isManim ? (
        <>
          <Field label={t("Quality")} width="w-[100px]">
            <AntSelect
              value={value.quality}
              onChange={(v) => update("quality", v as VisualizeFormConfig["quality"])}
              size="small"
              style={{ width: "100%" }}
              options={[
                { value: "low", label: t("Low") },
                { value: "medium", label: t("Medium") },
                { value: "high", label: t("High") },
              ]}
            />
          </Field>

          <Field label={t("Style Hint")} width="min-w-[160px] flex-1">
            <input
              type="text"
              value={value.style_hint}
              onChange={(e) => update("style_hint", e.target.value)}
              placeholder={t("Style, pacing, color...")}
              className={`${INPUT_CLS} w-full`}
            />
          </Field>
        </>
      ) : null}
    </>
  );

  if (collapsed === undefined) {
    return (
      <div className="flex flex-wrap items-end gap-x-3 gap-y-2 px-3.5 py-2.5">
        {body}
      </div>
    );
  }

  return (
    <CollapsibleConfigSection
      collapsed={collapsed}
      summary={summarizeVisualizeConfig(value, t)}
      onToggleCollapsed={onToggleCollapsed ?? (() => undefined)}
      bodyClassName="flex flex-wrap items-end gap-x-3 gap-y-2 px-3.5 pb-2.5"
    >
      {body}
    </CollapsibleConfigSection>
  );
});
