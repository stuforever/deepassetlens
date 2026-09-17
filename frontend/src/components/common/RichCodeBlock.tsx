/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/RichCodeBlock.tsx
 * （RichMarkdownRenderer 级联依赖，lazy 加载）。替换点：
 *  - "use client" 去；
 *  - 依赖包已安装（IA批6 N-16 react-syntax-highlighter）——下方 import 以 @ts-ignore
 *    承载类型；运行时渲染代码块需安装 react-syntax-highlighter@^16 后由 webpack 解析；
 *  - ./code-block-themes → 同目录既有 1:1 件；../../context/AppShellContext →
 *    ../../pages/tutor/admin/appShellContext（本仓既有 AppShellContext 移植件，
 *    codeBlockTheme/codeBlockShowLineNumbers/codeBlockWrapLongLines 字段一致）；
 *  - Tailwind 类逐项换内联样式；调用侧传入的 gap 由 className 字符串改为 style 对象
 *    （prop 更名 className → style，见 RichMarkdownRenderer 调用点登记）。
 * 其余逐字一致。
 */

// @ts-ignore 缺包登记：react-syntax-highlighter 未安装（见文件头）
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

import type { CSSProperties } from "react";
import {
  getCodeBlockTheme,
  getCodeBlockThemeBackground,
} from "./code-block-themes";
import { useAppShell } from "../../pages/tutor/admin/appShellContext";

const MONOSPACE =
  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace';

const PLAIN_LANGS = new Set(["", "text", "txt", "plain", "plaintext", "none"]);
const DEFAULT_CODE_BLOCK_BACKGROUND = "#1f2937";
const DEFAULT_CODE_BLOCK_FOREGROUND = "#e5e7eb";

function getCodeBlockThemeForeground(
  style: Record<string, React.CSSProperties>,
): string | undefined {
  const codeStyle = style['code[class*="language-"]'];
  if (codeStyle && typeof codeStyle.color === "string") {
    return codeStyle.color;
  }

  const preStyle = style['pre[class*="language-"]'];
  if (preStyle && typeof preStyle.color === "string") {
    return preStyle.color;
  }

  return undefined;
}

export default function RichCodeBlock({
  raw,
  lang,
  style,
}: {
  raw: string;
  lang: string;
  style?: CSSProperties;
}) {
  const { codeBlockTheme, codeBlockShowLineNumbers, codeBlockWrapLongLines } =
    useAppShell();
  const normalizedLang = (lang || "").toLowerCase();
  const isPlain = PLAIN_LANGS.has(normalizedLang);
  const syntaxTheme = getCodeBlockTheme(codeBlockTheme);
  const backgroundColor =
    getCodeBlockThemeBackground(syntaxTheme) ?? DEFAULT_CODE_BLOCK_BACKGROUND;
  const textColor =
    getCodeBlockThemeForeground(syntaxTheme) ?? DEFAULT_CODE_BLOCK_FOREGROUND;
  const syntaxLanguage = isPlain ? "text" : normalizedLang;

  return (
    <div
      className="md-code-block"
      style={{
        overflow: "hidden",
        borderRadius: 12,
        border: "1px solid var(--border, #e2e8f0)",
        ...(style || {}),
        backgroundColor,
        color: textColor,
      }}
    >
      {!isPlain ? (
        <div
          style={{
            borderBottom: "1px solid var(--border, #e2e8f0)",
            padding: "8px 12px",
            fontSize: 11,
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: textColor,
            opacity: 0.8,
          }}
        >
          {normalizedLang}
        </div>
      ) : null}
      <SyntaxHighlighter
        language={syntaxLanguage}
        style={syntaxTheme}
        PreTag="pre"
        customStyle={{
          margin: 0,
          borderRadius: 0,
          background: backgroundColor,
          color: textColor,
          padding: "1rem",
          fontSize: "0.875rem",
          lineHeight: "1.7",
          overflowX: codeBlockWrapLongLines ? "hidden" : "auto",
          whiteSpace: codeBlockWrapLongLines ? "pre-wrap" : "pre",
          wordWrap: codeBlockWrapLongLines ? "break-word" : "normal",
        }}
        codeTagProps={{
          className: "md-code-block__code",
          style: {
            fontFamily: MONOSPACE,
            ...(codeBlockWrapLongLines ? { wordWrap: "break-word" } : {}),
          },
        }}
        showLineNumbers={codeBlockShowLineNumbers}
        wrapLongLines={codeBlockWrapLongLines}
        // react-syntax-highlighter's highlight.js forces `display:flex` onto
        // each per-line span when BOTH wrapLongLines and showLineNumbers are
        // on (so the line-number gutter can align in a column). That flex
        // layout makes each token span a flex item with the default
        // `min-width:auto`, which cannot shrink below content size — so a
        // long unbreakable token overflows the line wrapper and defeats
        // `overflow-wrap:break-word` set on <pre>/<code>. Overriding the
        // per-line wrapper back to `display:block` lets the tokens flow as
        // normal inline content, where `overflow-wrap:break-word` can
        // actually break long tokens.
        lineProps={
          codeBlockWrapLongLines && codeBlockShowLineNumbers
            ? { style: { display: "block" } }
            : undefined
        }
      >
        {raw}
      </SyntaxHighlighter>
    </div>
  );
}
