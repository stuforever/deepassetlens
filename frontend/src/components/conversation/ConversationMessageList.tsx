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
}>(({ msg, isLast, canDelete, liveMetaInfo, liveFinalAnswer, onSelectRecommendation, onDeleteMessage, onHITLDecision }) => (
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
          {/* 思考面板：读占位消息自身的 payload，实时渲染 */}
          {msg.payload?.thinkStream && msg.payload.thinkStream.length > 0 ? (
            <ThinkStream
              items={msg.payload.thinkStream}
              active={true}
              liveStatus={msg.payload?.live_text}
              metaInfo={msg.payload?.live_meta}
            />
          ) : null}
          {/*
            交付体验演进 v2 输出区状态机（用户定调版）：全程只有两种形态——状态行 或 完整交付卡。
            四态推导：正在理解问题 → 检索数据中(有工具步骤) → 答案生成中(answer_generating)
            → 答案整理中(final_answer 已到/answer_finalizing，覆盖 rubric 尾巴与收尾期)。
            answer_draft token 已全部丢弃（批1-A 双写回退），正文唯一来源 = done 时结构化渲染；
            步骤明细照旧进 ThinkStream 折叠区；不变式：不存在第三种形态（无裸文本期）。
          */}
          {(() => {
            const p = msg.payload || {};
            const statusText = (p.final_answer || p.answer_finalizing)
              ? '答案整理中，正以结构化方式输出，请稍候…'
              : p.answer_generating
                ? '答案生成中…'
                : (p.thinkStream && p.thinkStream.length > 0)
                  ? '检索数据中…'
                  : '正在理解问题…';
            return (
              <Space>
                <Spin size="small" />
                <Text strong>{statusText}</Text>
              </Space>
            );
          })()}
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
));
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
