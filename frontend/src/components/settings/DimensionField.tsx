/**
 * 复刻自 DeepTutor 原仓 web/components/settings/DimensionField.tsx（整件 1:1，批5 5.2）。
 * 替换点：
 * - 去 "use client"；react-i18next 的 t('English') → 直接内联中文
 *   （映射源 web/locales/zh/app.json：Auto (probe on next test)/Custom…/Use a supported
 *   value/Detected/Use this/Source: detected from API probe 六键，均已收录）；
 * - Tailwind 类（space-y-1.5 / text-[11px] / flex …）逐项换为内联样式，
 *   颜色用原仓语义 var(--xxx, 兜底值) 承载（与同批 Toggle.tsx 口径一致）；
 * - 原生 <select>/<input>/<button> → antd Select/Input/Button
 *   （value/onChange/disabled/data-testid 行为契约逐字保留）。
 * lucide-react→antd 图标登记：本件源码未使用 lucide 图标，无映射。
 */
import React, { useState } from "react";
import { Button, Input, Select } from "antd";

import type { CatalogModel, EmbeddingCapabilities } from "./SettingsContext";
import { nativeSelectClass, selectOptionClass } from "./shared";

const CUSTOM_DIM_SENTINEL = "__custom__";
const AUTO_DIM_SENTINEL = "";

function parseSupportedCsv(csv: string | undefined): number[] {
  if (!csv) return [];
  return csv
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => Number(s))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function sourceBadge(
  source: string | undefined,
): { label: string; tone: "muted" | "ok" | "warn" } | null {
  if (source === "detected") {
    // 原仓 t("Source: detected from API probe")（zh：来源：API 测试检测）
    return { label: "来源：API 测试检测", tone: "ok" };
  }
  return null;
}

export function DimensionField({
  activeModel,
  activeBinding,
  capabilities,
  embeddingDefaultDim,
  inputClass,
  onChangeDimension,
}: {
  activeModel: CatalogModel;
  activeBinding?: string;
  capabilities: EmbeddingCapabilities | null;
  embeddingDefaultDim: (binding?: string) => string;
  inputClass: string;
  onChangeDimension: (value: string) => void;
}) {
  const fallback = embeddingDefaultDim(activeBinding);
  const rawValue = activeModel.dimension ?? "";
  const isEmpty = rawValue === "";
  const currentNum = isEmpty ? NaN : Number(rawValue);

  const liveSupported = capabilities?.supported_dimensions;
  const cachedSupported = parseSupportedCsv(activeModel.supported_dimensions);
  const supported =
    liveSupported && liveSupported.length > 0 ? liveSupported : cachedSupported;
  const supportsVariable =
    capabilities?.supports_variable_dimensions ?? supported.length > 1;

  const useDropdown = supported.length > 1 && supportsVariable;
  const currentInList =
    Number.isFinite(currentNum) && supported.includes(currentNum);
  const [customRequested, setCustomRequested] = useState<boolean>(false);
  const customMode =
    customRequested || (useDropdown && !isEmpty && !currentInList);

  const detected = capabilities?.detected_dim;
  const showDetectedBadge =
    typeof detected === "number" &&
    detected > 0 &&
    detected !== currentNum &&
    !isEmpty;

  const sourceInfo = sourceBadge(capabilities?.active_dim_source);
  const disabled = activeModel.send_dimensions === false;

  const handleSelect = (value: string) => {
    if (value === CUSTOM_DIM_SENTINEL) {
      setCustomRequested(true);
      return;
    }
    setCustomRequested(false);
    onChangeDimension(value);
  };

  const dropdownValue = isEmpty
    ? AUTO_DIM_SENTINEL
    : currentInList
      ? String(currentNum)
      : CUSTOM_DIM_SENTINEL;

  return (
    <div
      data-testid="service-dimension-field"
      style={{ display: "flex", flexDirection: "column", gap: 6 }}
    >
      {useDropdown && !customMode ? (
        <Select
          className={nativeSelectClass}
          style={{ width: "100%" }}
          value={dropdownValue}
          onChange={handleSelect}
          disabled={disabled}
          data-testid="service-dimension-input"
        >
          <Select.Option
            className={selectOptionClass}
            value={AUTO_DIM_SENTINEL}
          >
            自动（下次测试时检测）
          </Select.Option>
          {supported.map((dim) => (
            <Select.Option
              className={selectOptionClass}
              key={dim}
              value={String(dim)}
            >
              {dim}
            </Select.Option>
          ))}
          <Select.Option className={selectOptionClass} value={CUSTOM_DIM_SENTINEL}>
            自定义…
          </Select.Option>
        </Select>
      ) : (
        <Input
          className={inputClass}
          value={rawValue}
          placeholder={fallback}
          onChange={(e) => onChangeDimension(e.target.value)}
          disabled={disabled}
          inputMode="numeric"
          data-testid="service-dimension-input"
        />
      )}
      {useDropdown && customMode && (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setCustomRequested(false);
            if (isEmpty) {
              return;
            }
            const closest = supported.reduce((acc, dim) =>
              Math.abs(dim - currentNum) < Math.abs(acc - currentNum)
                ? dim
                : acc,
            );
            onChangeDimension(String(closest));
          }}
          style={{
            fontSize: 11,
            padding: 0,
            height: "auto",
            width: "fit-content",
            color: "var(--muted-foreground, #64748b)",
            textDecoration: "underline",
            textUnderlineOffset: 2,
          }}
        >
          使用受支持的值
        </Button>
      )}
      {sourceInfo && (
        <div
          style={{
            fontSize: 11,
            color:
              sourceInfo.tone === "warn"
                ? "var(--amber-600, #d97706)"
                : sourceInfo.tone === "ok"
                  ? "var(--emerald-600, #059669)"
                  : "var(--muted-foreground, #64748b)",
          }}
        >
          {sourceInfo.label}
        </div>
      )}
      {showDetectedBadge && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 11,
            color: "var(--muted-foreground, #64748b)",
          }}
        >
          <span>
            检测到: <strong>{detected}d</strong>
          </span>
          <Button
            size="small"
            onClick={() => onChangeDimension(String(detected))}
            disabled={disabled}
            style={{
              fontSize: 10,
              height: 20,
              padding: "0 6px",
              borderRadius: 6,
              color: "var(--foreground, #0f172a)",
            }}
          >
            使用该值
          </Button>
        </div>
      )}
    </div>
  );
}
