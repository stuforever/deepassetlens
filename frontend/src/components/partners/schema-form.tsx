/**
 * 复刻自 DeepTutor 原仓 web/components/partners/schema-form.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；Tailwind 类逐项换内联样式（focus 边框用 onFocus/onBlur
 * 事件直写；focus 样式状态与互斥渲染分支共享一个 state，行为一致）。源件无 i18n
 * 调用，aria/title/提示文案保留英文原文（与源逐字一致）。
 * lucide-react→antd 图标登记：Eye → EyeOutlined；EyeOff → EyeInvisibleOutlined。
 *
 * Schema-driven channel config form, shared by the partner Channels panel.
 * Renders a generic editor for ANY channel (built-in or plugin) from the
 * Pydantic JSON schema served by `GET /api/v1/partners/channels/schema`.
 */

import { useState } from "react";
import { Select as AntSelect } from "antd"; // R5批②：原生 select → antd（R#2 续批，enum 显式映射）
import { EyeInvisibleOutlined, EyeOutlined } from "@ant-design/icons";

export type JsonSchema = {
  type?: string | string[];
  title?: string;
  description?: string;
  default?: unknown;
  enum?: unknown[];
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  anyOf?: JsonSchema[];
};

/** Pick the first non-null variant of an `anyOf` and merge its meta. */
export function resolveSchemaVariant(s: JsonSchema): JsonSchema {
  if (!s.anyOf) return s;
  const first = s.anyOf.find((v) => v.type !== "null") ?? s.anyOf[0];
  return {
    ...first,
    title: s.title ?? first.title,
    description: s.description ?? first.description,
  };
}

/** True iff this schema's value can be `null` (e.g. `Optional[str]`). */
export function isNullable(s: JsonSchema): boolean {
  if (Array.isArray(s.type) && s.type.includes("null")) return true;
  if (s.anyOf?.some((v) => v.type === "null")) return true;
  return false;
}

/** Default value for a property when the live config doesn't set it. */
export function defaultFor(s: JsonSchema): unknown {
  if (s.default !== undefined) return s.default;
  const v = resolveSchemaVariant(s);
  switch (v.type) {
    case "boolean":
      return false;
    case "integer":
    case "number":
      return 0;
    case "array":
      return [];
    case "object":
      return {};
    case "string":
    default:
      return "";
  }
}

/** Title-case a snake_case key when no `title` is provided. */
function humaniseKey(k: string): string {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const INPUT_BASE: React.CSSProperties = {
  borderRadius: 8,
  border: "1px solid var(--border, #e2e8f0)",
  background: "transparent",
  padding: "6px 12px",
  fontSize: 13,
  outline: "none",
  transition: "border-color 150ms",
};

function focusStyle(focused: boolean): React.CSSProperties {
  return {
    ...INPUT_BASE,
    borderColor: focused
      ? "var(--ring, #2563eb)"
      : "var(--border, #e2e8f0)",
  };
}

function FieldLabel({
  label,
  description,
}: {
  label: string;
  description?: string;
}) {
  return (
    <label
      style={{
        display: "block",
        marginBottom: 4,
        fontSize: 12,
        fontWeight: 500,
        color: "var(--foreground, #0f172a)",
      }}
    >
      {label}
      {description && (
        <span style={{ marginLeft: 4, fontWeight: 400, opacity: 0.7 }}>
          — {description}
        </span>
      )}
    </label>
  );
}

/** Free-form dict field (object without fixed properties) → JSON textarea. */
function JsonObjectField({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description?: string;
  value: unknown;
  onChange: (next: unknown) => void;
}) {
  const [draft, setDraft] = useState(() => {
    const obj =
      value && typeof value === "object"
        ? (value as Record<string, unknown>)
        : {};
    return Object.keys(obj).length ? JSON.stringify(obj, null, 2) : "";
  });
  const [invalid, setInvalid] = useState(false);
  const [focused, setFocused] = useState(false);
  return (
    <div>
      <FieldLabel
        label={label}
        description={description ?? 'JSON object, e.g. {"key": "value"}'}
      />
      <textarea
        value={draft}
        onChange={(e) => {
          const text = e.target.value;
          setDraft(text);
          if (!text.trim()) {
            setInvalid(false);
            onChange({});
            return;
          }
          try {
            const parsed: unknown = JSON.parse(text);
            if (
              parsed &&
              typeof parsed === "object" &&
              !Array.isArray(parsed)
            ) {
              setInvalid(false);
              onChange(parsed);
            } else {
              setInvalid(true);
            }
          } catch {
            setInvalid(true);
          }
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        rows={4}
        style={{
          ...focusStyle(focused),
          width: "100%",
          padding: "8px 12px",
          fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
          resize: "vertical",
        }}
      />
      {invalid && (
        <p
          style={{
            marginTop: 4,
            fontSize: 11,
            color: "#d97706",
            margin: "4px 0 0",
          }}
        >
          Invalid JSON — value not applied.
        </p>
      )}
    </div>
  );
}

/** Generic field renderer — recursive for nested objects. */
export function SchemaField({
  fieldKey,
  schema,
  value,
  onChange,
  secretFields,
  path,
  showSecretFor,
  toggleSecret,
}: {
  fieldKey: string;
  schema: JsonSchema;
  value: unknown;
  onChange: (next: unknown) => void;
  secretFields: Set<string>;
  path: string;
  showSecretFor: Set<string>;
  toggleSecret: (path: string) => void;
}) {
  const [focused, setFocused] = useState(false);
  const [revealHover, setRevealHover] = useState(false);
  const v = resolveSchemaVariant(schema);
  const label = schema.title || v.title || humaniseKey(fieldKey);
  const description = schema.description || v.description;
  const isSecret = secretFields.has(path);
  const enumValues = (v.enum ?? schema.enum) as unknown[] | undefined;

  // Boolean → checkbox row (label inline).
  if (v.type === "boolean") {
    return (
      <label
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 8,
          fontSize: 13,
        }}
      >
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
          style={{ marginTop: 2 }}
        />
        <span>
          {label}
          {description && (
            <span
              style={{
                marginLeft: 4,
                fontSize: 11,
                color: "var(--muted-foreground, #64748b)",
              }}
            >
              — {description}
            </span>
          )}
        </span>
      </label>
    );
  }

  // Enum / Literal → select.
  if (Array.isArray(enumValues) && enumValues.length > 0) {
    return (
      <div>
        <FieldLabel label={label} description={description} />
        <AntSelect
          value={String(value ?? "")}
          onChange={(v) => onChange(v)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{ ...focusStyle(focused), width: "100%" }}
          options={enumValues.map((opt) => ({
            value: String(opt),
            label: String(opt),
          }))}
        />
      </div>
    );
  }

  // Array of strings → textarea (one per line).
  if (v.type === "array" && (v.items?.type === "string" || !v.items)) {
    const lines = Array.isArray(value) ? (value as unknown[]).map(String) : [];
    return (
      <div>
        <FieldLabel
          label={label}
          description={description ?? "One value per line"}
        />
        <textarea
          value={lines.join("\n")}
          onChange={(e) =>
            onChange(
              e.target.value
                .split("\n")
                .map((s) => s.trim())
                .filter(Boolean),
            )
          }
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          rows={Math.max(3, Math.min(8, lines.length + 1))}
          style={{
            ...focusStyle(focused),
            width: "100%",
            padding: "8px 12px",
            fontFamily:
              'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            resize: "vertical",
          }}
        />
      </div>
    );
  }

  // Nested object → recursive fieldset.
  if (v.type === "object" && v.properties) {
    const obj = (value && typeof value === "object" ? value : {}) as Record<
      string,
      unknown
    >;
    return (
      <fieldset
        style={{
          borderRadius: 8,
          border: "1px solid var(--border, #e2e8f0)",
          padding: "10px 12px",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          margin: 0,
        }}
      >
        <legend
          style={{
            padding: "0 4px",
            fontSize: 12,
            fontWeight: 500,
            color: "var(--muted-foreground, #64748b)",
          }}
        >
          {label}
        </legend>
        {description && (
          <p
            style={{
              fontSize: 11,
              color: "var(--muted-foreground, #64748b)",
              margin: 0,
            }}
          >
            {description}
          </p>
        )}
        {Object.entries(v.properties).map(([k, child]) => (
          <SchemaField
            key={k}
            fieldKey={k}
            schema={child}
            value={obj[k] ?? defaultFor(child)}
            onChange={(next) => onChange({ ...obj, [k]: next })}
            secretFields={secretFields}
            path={path ? `${path}.${k}` : k}
            showSecretFor={showSecretFor}
            toggleSecret={toggleSecret}
          />
        ))}
      </fieldset>
    );
  }

  // Free-form dict (additionalProperties only) → JSON textarea.
  if (v.type === "object") {
    return (
      <JsonObjectField
        label={label}
        description={description}
        value={value}
        onChange={onChange}
      />
    );
  }

  // Integer/number → number input.
  if (v.type === "integer" || v.type === "number") {
    return (
      <div>
        <FieldLabel label={label} description={description} />
        <input
          type="number"
          value={typeof value === "number" ? value : ""}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === "") onChange(isNullable(schema) ? null : 0);
            else
              onChange(
                v.type === "integer" ? parseInt(raw, 10) : parseFloat(raw),
              );
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{ ...focusStyle(focused), width: 160 }}
        />
      </div>
    );
  }

  // Default: string input (with secret reveal handling).
  const reveal = showSecretFor.has(path);
  const strVal = value == null ? "" : String(value);
  return (
    <div>
      <FieldLabel label={label} description={description} />
      <div style={{ position: "relative" }}>
        <input
          type={isSecret && !reveal ? "password" : "text"}
          autoComplete={isSecret ? "new-password" : "off"}
          spellCheck={!isSecret}
          value={strVal}
          onChange={(e) => {
            const next = e.target.value;
            // Empty optional strings persist as null (matches Pydantic's
            // `Optional[str]` default and avoids "" sneaking past validators).
            onChange(next === "" && isNullable(schema) ? null : next);
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            ...focusStyle(focused),
            width: "100%",
            padding: "8px 12px",
            paddingRight: isSecret ? 40 : 12,
            fontFamily: isSecret
              ? 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
              : undefined,
          }}
        />
        {isSecret && (
          <button
            type="button"
            onClick={() => toggleSecret(path)}
            onMouseEnter={() => setRevealHover(true)}
            onMouseLeave={() => setRevealHover(false)}
            style={{
              position: "absolute",
              right: 4,
              top: "50%",
              transform: "translateY(-50%)",
              borderRadius: 6,
              border: "none",
              padding: 6,
              background: revealHover ? "var(--muted, #f1f5f9)" : "transparent",
              color: revealHover
                ? "var(--foreground, #0f172a)"
                : "var(--muted-foreground, #64748b)",
              cursor: "pointer",
              transition: "background-color 150ms, color 150ms",
            }}
            aria-label={reveal ? "Hide secret" : "Show secret"}
            title={reveal ? "Hide secret" : "Show secret"}
          >
            {reveal ? (
              <EyeInvisibleOutlined style={{ fontSize: 16 }} />
            ) : (
              <EyeOutlined style={{ fontSize: 16 }} />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
