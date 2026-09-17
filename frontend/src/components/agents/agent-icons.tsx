/**
 * IA批5 lib 补件：路径适配 re-export——tupu 既有同源 1:1 件在
 * pages/tutor/h5/h5shared/agent-icons.tsx（导出逐字一致：六 Glyph+PartnerGlyph+agentGlyph）。
 * components/settings 家族按源路径 ../agents/agent-icons 消费——此处不复制实现，仅转发。
 */
export {
  ClaudeGlyph,
  CodexGlyph,
  GeminiGlyph,
  KimiGlyph,
  MimoGlyph,
  OpencodeGlyph,
  PartnerGlyph,
  agentGlyph,
} from "../../pages/tutor/h5/h5shared/agent-icons";
export type { AgentGlyph } from "../../pages/tutor/h5/h5shared/agent-icons";
