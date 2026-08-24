import React from 'react';
import { Alert, Button, Card, Skeleton, Space, Spin, Tag, Typography, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import ThinkStream from './ThinkStream';
import FinalAnswer from './FinalAnswer';
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
            批10③ 单帧交付·骨架卡（交付体验演进 §五）：loading 态收到首个实质事件
            （sql_result / 首 token）即立起交付卡骨架——结果区自始至终只有一张卡，
            所有元素都是槽位，不存在「裸文本期」：
              ├ 标题行：「查询结果」+ 徽标占位「复核中…」（done 后由完成态 Canvas 补终值）
              ├ 数据表槽：sql_result 到达即入卡（先于答案 3s+）
              └ 正文槽：answer_draft/streaming_answer 流进槽位（有骨架的流式=报告在写）
          */}
          {(msg.payload?.sql_result || msg.payload?.streaming_answer || msg.payload?.final_answer
            || (msg.payload?.finalTokens && msg.payload.finalTokens.length > 0)) ? (
            <Space direction="vertical" style={{ width: '100%' }} size={6}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--text-primary)', letterSpacing: '-0.01em', paddingLeft: 8, borderLeft: '3px solid var(--ant-primary-color, #1677ff)' }}>
                  查询结果
                </h2>
                <Tag color="processing" style={{ marginLeft: 10, fontSize: 11, lineHeight: '18px', padding: '0 8px', borderRadius: 999 }}>
                  <Spin size="small" style={{ marginRight: 4 }} />{msg.payload?.answer_revising ? '校验修订中…' : '复核中…'}
                </Tag>
              </div>
              {/* 正文槽：token 逐字流式（批1-A 直出能力保留，宿主改为卡内槽位） */}
              {msg.payload?.finalTokens && msg.payload.finalTokens.length > 0 ? (
                <FinalAnswer answer="" tokens={msg.payload.finalTokens} isStreaming={true} />
              ) : (msg.payload?.final_answer || msg.payload?.streaming_answer) ? (
                <FinalAnswer answer={msg.payload?.final_answer || msg.payload?.streaming_answer || ''} tokens={[]} isStreaming={!msg.payload?.final_answer} />
              ) : null}
              {/* 数据表槽：sql_result 到达即渲染（row_count>0 且有列，口径同完成态 showTable） */}
              {(msg.payload?.sql_result?.row_count ?? 0) > 0 && !!msg.payload?.sql_result?.columns?.length ? (
                <SqlResultTable data={msg.payload.sql_result} />
              ) : null}
            </Space>
          ) : (
            <Space>
              <Spin size="small" />
              <Text strong>{msg.payload?.live_text || msg.text || '正在思考...'}</Text>
            </Space>
          )}
          {(!msg.payload?.thinkStream || msg.payload.thinkStream.length === 0)
            && !msg.payload?.finalTokens?.length && !msg.payload?.final_answer
            && !msg.payload?.streaming_answer && !msg.payload?.sql_result ? (
            <Skeleton active paragraph={{ rows: 1 }} title={false} />
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
