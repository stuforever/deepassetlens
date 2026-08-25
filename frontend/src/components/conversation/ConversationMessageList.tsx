import React from 'react';
import { Alert, Button, Card, Space, Spin, Typography, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import ThinkStream from './ThinkStream';
import AssistantCanvas from './AssistantCanvas';
import ContractCardsPanel from './contractCards/ContractCardsPanel';
import SqlResultTable from './SqlResultTable';
import type { ChatMessage, ConversationCardAction, ConversationSceneConfig } from './types';

const { Text } = Typography;

/**
 * 批13-O 单一状态源 = 框架事件流的实时投影（后端零新增协议）。
 * 状态行只显示「现在进行时」；步骤卡（ThinkStream 折叠区）显示「过去」轨迹+耗时摘要——
 * 二者永不出现相同文案；联动感来自交接瞬间（事件落入步骤卡时状态行立刻切向下一动作）。
 * 全部信号来自 payload.thinkStream 时间序（task/input_summary/phase/duration_ms/started_at_ms），
 * 纯前端派生，无新增字段。
 */
type LiveStatus = { text: string; flashMs: number };

const _shortParams = (s?: string): string => {
  if (!s) return '';
  const t = s.replace(/^输入参数：/, '').replace(/[{}'"]/g, ' ').replace(/\s+/g, ' ').trim();
  return t.length > 36 ? t.slice(0, 36) + '…' : t;
};

const deriveLiveStatus = (p: any): LiveStatus => {
  const ts: any[] = p?.thinkStream || [];
  // 交付期：final/answer_committed 已到（覆盖 rubric 尾巴与收尾期）
  if (p.final_answer || p.answer_finalizing)
    return { text: '答案整理中，正以结构化方式输出，请稍候…', flashMs: 0 };
  // 答案生成期（v2 用户定调文案保留）
  if (p.answer_generating) return { text: '答案生成中…', flashMs: 0 };
  // 推理轮次可靠信号：ReAct 循环「思考→工具→思考→…」，第 N 轮推理前恰有 N-1 个工具步骤
  // （decision_draft 的 round_id 归并不稳定，不作计数依据）
  const toolCount = ts.filter((t) => t.kind === 'skill' || t.kind === 'plan').length;
  const roundNo = toolCount + 1;
  // 工具期：running 步骤 → {工具中文名}·{参数摘要}
  const running = ts.find((t) => t.phase === 'running');
  if (running)
    return { text: `${running.task || running.tool_name || '执行工具'}·${_shortParams(running.input_summary)}`, flashMs: 0 };
  // 完成闪示：最近终态步骤在 2.5s 内 → 完成(x.xs)；done_at = started_at_ms + duration_ms
  for (let i = ts.length - 1; i >= 0; i--) {
    const t = ts[i];
    if ((t.phase === 'done' || t.phase === 'error') && t.started_at_ms && t.duration_ms != null) {
      const remain = t.started_at_ms + t.duration_ms + 2500 - Date.now();
      if (remain > 0)
        return { text: `${t.task}${t.phase === 'error' ? '执行失败' : '完成'}(${(t.duration_ms / 1000).toFixed(1)}s)`, flashMs: remain };
      break; // 最近终态已过闪示窗口
    }
    if (t.kind === 'decision') break; // 最近活动是推理轮，跳过完成闪示
  }
  // 思考期 / 工具间间隙：已有任一步骤历史 -> 下一动作必是新一轮推理（联动感：交接瞬间即切向）
  if (ts.length > 0) return { text: `小探正在推理 · 第${roundNo}轮`, flashMs: 0 };
  // 编排期初始 / 无信号兜底占位（「小探正在运行中」降级为兜底语义）
  return { text: '小探正在理解问题…', flashMs: 0 };
};

/**
 * 单条消息行：React.memo 隔离非末条消息的流式重渲染。
 * 关键前提（由父级保证）：
 *   - live 系列 props 只传给末条（isLast），其余行拿 stable undefined；
 *   - 回调引用稳定（父级 useCallback），避免 memo 失效。
 */
const MessageRow = React.memo<{
  msg: ChatMessage;
  isLast: boolean;
  canDelete: boolean;
  liveMetaInfo?: string;
  liveFinalAnswer?: string;
  onSelectRecommendation?: (rec: any) => void;
  onDeleteMessage?: (msgId: string) => void;
  onHITLDecision?: (interruptId: string, approve: boolean) => void;
}>(({ msg, isLast, canDelete, liveMetaInfo, liveFinalAnswer, onSelectRecommendation, onDeleteMessage, onHITLDecision }) => {
  // 批13-O：完成闪示窗口退出需要一次重渲（无新事件到来时「完成(x.xs)」短暂显示后切回兜底）
  const [, _tick] = React.useReducer((x: number) => x + 1, 0);
  const _live = msg.loading ? deriveLiveStatus(msg.payload) : null;
  React.useEffect(() => {
    if (!_live?.flashMs) return;
    const timer = setTimeout(_tick, _live.flashMs + 120);
    return () => clearTimeout(timer);
  }, [_live?.text, _live?.flashMs]);
  return (
  <div className="msg-row" style={{ position: 'relative', display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', width: '100%' }}>
    {canDelete ? (
      <Popconfirm title="删除该条消息？" okText="删除" cancelText="取消" onConfirm={() => onDeleteMessage!(msg.id)}>
        <DeleteOutlined className="msg-del" style={{ position: 'absolute', top: 4, right: 4, zIndex: 10, fontSize: 13, color: 'var(--text-tertiary)', cursor: 'pointer', padding: 4 }} />
      </Popconfirm>
    ) : null}
    <Card
      size="small"
      bordered={false}
      style={{
        width: msg.role === 'user' ? 'min(1200px, 72%)' : '100%',
        maxWidth: '100%',
        background: msg.role === 'user' ? 'var(--color-primary-bg)' : 'transparent',
        boxShadow: 'none',
      }}
      title={undefined}
      bodyStyle={msg.role === 'user' ? { padding: '6px 12px' } : { padding: '0' }}
    >
      {msg.role === 'user' ? (
        /* B2 美化：用户问题 = 左主色竖线 + 文本 + 12px 时间戳，与回答区分 */
        <div style={{ borderLeft: `3px solid var(--color-primary)`, paddingLeft: 10, width: '100%' }}>
          <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{msg.text}</div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
            {(() => {
              const m = /(\d{13})/.exec(msg.id || '');
              if (!m) return '';
              const d = new Date(Number(m[1]));
              if (Number.isNaN(d.getTime())) return '';
              const p = (n: number) => String(n).padStart(2, '0');
              return `${p(d.getHours())}:${p(d.getMinutes())}`;
            })()}
          </div>
        </div>
      ) : msg.loading ? (
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          {/* S5（HITL v2）：表/catalog 不存在 -> 人审横条（流式暂停等待批准/拒绝；批准后恢复同 thread 续跑） */}
          {msg.payload?.hitl_interrupt && msg.payload.hitl_interrupt.interrupt_id && onHITLDecision ? (
            <Alert
              type="warning"
              showIcon
              message="需要你确认：查询的表/catalog 不存在"
              description={
                <div style={{ fontSize: 12 }}>
                  <div style={{ marginBottom: 4 }}>
                    {msg.payload.hitl_interrupt.reason} {msg.payload.hitl_interrupt.proposal}
                  </div>
                  <Space size={8}>
                    <Button size="small" type="primary" onClick={() => onHITLDecision(msg.payload!.hitl_interrupt!.interrupt_id, true)}>批准重试</Button>
                    <Button size="small" onClick={() => onHITLDecision(msg.payload!.hitl_interrupt!.interrupt_id, false)}>拒绝</Button>
                  </Space>
                </div>
              }
              style={{ maxWidth: 640 }}
            />
          ) : null}
          {/* 受控 Skill 问答平台 v2：流式运行中即渲染受控卡片（route/contract 事件一到即显示，默认折叠状态条） */}
          {(msg.payload?.route || msg.payload?.contract) ? (
            <ContractCardsPanel
              route={msg.payload.route}
              contract={msg.payload.contract}
              policyEvents={msg.payload.policy_events}
              templateEvents={msg.payload.template_events}
            />
          ) : null}
          {/* 思考面板：读占位消息自身的 payload，实时渲染。
              批13-O：liveStatus = 框架事件流实时投影（deriveLiveStatus），
              上移至 ThinkStream 头部标题位替换静态「正在定位数据」——进展在最上面动态展示 */}
          {msg.payload?.thinkStream && msg.payload.thinkStream.length > 0 ? (
            <ThinkStream
              items={msg.payload.thinkStream}
              active={true}
              liveStatus={_live?.text}
              metaInfo={msg.payload?.live_meta}
            />
          ) : null}
          {/* 批13-O：thinkStream 为空时（编排期首帧）状态行独立显示，保证首个可见反馈不依赖步骤产生 */}
          {(!msg.payload?.thinkStream || msg.payload.thinkStream.length === 0) && _live ? (
            <Space>
              <Spin size="small" />
              <Text strong>{_live.text}</Text>
            </Space>
          ) : null}
          {/* 可选 TUPU_EARLY_TABLE 开关（默认关）：表格属结构化元素可提前入卡，正文仍等 done */}
          {(typeof window !== 'undefined' && window.localStorage.getItem('TUPU_EARLY_TABLE') === '1'
            && (msg.payload?.sql_result?.row_count ?? 0) > 0 && !!msg.payload?.sql_result?.columns?.length) ? (
            <SqlResultTable data={msg.payload.sql_result} />
          ) : null}
        </Space>
      ) : (
        <AssistantCanvas
          payload={msg.payload}
          isLast={isLast}
          liveMetaInfo={liveMetaInfo}
          liveFinalAnswer={liveFinalAnswer}
          onSelectRecommendation={onSelectRecommendation}
        />
      )}
    </Card>
  </div>
  );
});
MessageRow.displayName = 'MessageRow';

const ConversationMessageList: React.FC<{
  messages: ChatMessage[];
  sceneConfig: ConversationSceneConfig;
  loading?: boolean;
  liveStatus?: string;
  liveTokens?: string[];
  liveFinalAnswer?: string;
  liveRecommendations?: Array<{ label: string; shortcut?: string }>;
  liveMetaInfo?: string;
  confirmedData?: Record<string, any>;
  onCardAction?: (action: ConversationCardAction) => void;
  onSelectRecommendation?: (rec: any) => void;
  onExecuteSql?: () => void;
  onEntityClick?: (entityCode: string, entityName?: string) => void;
  onDeleteMessage?: (msgId: string) => void;
  /** S5（HITL v2）：批准/拒绝人审中断（interrupt_id, approve） */
  onHITLDecision?: (interruptId: string, approve: boolean) => void;
}> = ({
  messages,
  sceneConfig,
  liveFinalAnswer,
  liveMetaInfo,
  onSelectRecommendation,
  onDeleteMessage,
  onHITLDecision,
}) => {
  if (messages.length === 0) {
    return (
      <Alert
        type="info"
        showIcon
        message={sceneConfig.emptyMessage || '暂无对话'}
        description={sceneConfig.emptyDescription || '请输入问题开始对话。'}
      />
    );
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      <style>{`.msg-row:hover .msg-del{opacity:1!important}.msg-del{opacity:0.35;transition:opacity .15s}`}</style>
      {messages.map((msg, msgIdx) => {
        const isLast = msgIdx === messages.length - 1;
        return (
          <MessageRow
            key={msg.id}
            msg={msg}
            isLast={isLast}
            canDelete={!!(onDeleteMessage && !msg.loading)}
            liveMetaInfo={isLast ? liveMetaInfo : undefined}
            liveFinalAnswer={isLast ? liveFinalAnswer : undefined}
            onSelectRecommendation={onSelectRecommendation}
            onDeleteMessage={onDeleteMessage}
            onHITLDecision={onHITLDecision}
          />
        );
      })}
    </Space>
  );
};

export default ConversationMessageList;
