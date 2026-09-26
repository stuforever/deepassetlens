import { Select as AntSelect } from "antd";

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
            // manim_video/manim_image 入口下线（2026-09-26 评估裁定：渲染沙箱未部署
            // 且镜像无 manim，选择即必败；R6 随沙箱部署恢复）。
          ]}
        />
      </Field>
      {/* isManim 附加旋钮（quality/style_hint）随 manim 入口下线一并移除 */}
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
