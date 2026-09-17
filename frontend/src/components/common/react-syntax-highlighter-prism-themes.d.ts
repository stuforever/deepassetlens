// 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/react-syntax-highlighter-prism-themes.d.ts。
// 作用：tupu 未安装 react-syntax-highlighter（缺包登记，勿私装），本声明让 code-block-themes.ts
// 对 40 个 prism 主题样式文件的 import 通过类型检查；运行时渲染需安装该包后由 webpack 解析。
declare module "react-syntax-highlighter/dist/esm/styles/prism/*" {
  import type { CSSProperties } from "react";

  const theme: Record<string, CSSProperties>;
  export default theme;
}
