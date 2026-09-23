/**
 * 批①a（v4§十二.2/附录A.7）：全站思考链文案映射表——骨架组件唯一（ThinkingChain），
 * 个性化仅在内容层（agentName/标题/摘要文案）；步骤与工具名来自后端事件流本体。
 * 问数=现状 ThinkStream 文案逐字（「问数卡配置=现文案」，行为零变化）；
 * 私塾=h5 同款「小塾」语义（§12.2 专家卡 thinking_texts 的前端常量落位）。
 */
export interface ThinkingTexts {
  /** 专家名（状态行主语：小探/小塾） */
  agentName: string;
  /** 完成态标题（折叠行）：{agentName} 已准备好答案 */
  idleTitle: string;
  /** 生成中无 liveStatus 时的标题回落 */
  activeTitleFallback: string;
  /** 生成中摘要：正在推理 · 已定位 N 步 */
  runningMeta: (steps: number) => string;
  /** 完成摘要：推理完成 · 定位 N 步 */
  doneMeta: (steps: number) => string;
}

export const thinkingTexts: Record<string, ThinkingTexts> = {
  wenshu: {
    agentName: '小探',
    idleTitle: '小探 已准备好答案',
    activeTitleFallback: '小探 正在定位数据...',
    runningMeta: (steps) => `正在推理 · 已定位 ${steps} 步`,
    doneMeta: (steps) => `推理完成 · 定位 ${steps} 步`,
  },
  sishu: {
    agentName: '小塾',
    idleTitle: '小塾 已准备好答案',
    activeTitleFallback: '小塾 正在思考...',
    runningMeta: (steps) => `正在思考 · 已进行 ${steps} 步`,
    doneMeta: (steps) => `思考完成 · 共 ${steps} 步`,
  },
};

/** 专家文案取用（未知 expertId 回落 wenshu——骨架永不因配置缺失而崩）。 */
export function textsFor(expertId?: string): ThinkingTexts {
  return (expertId && thinkingTexts[expertId]) || thinkingTexts.wenshu;
}
