/**
 * MessageActions（批①a——v4§二.3/§九 操作条 5 项）：每条 AI 回答底部动作条。
 * 复制 / 保存到笔记（复用 SaveToNotebookModal 既有机制）/ 下载 Markdown（前端 Blob）/
 * 点赞 / 点踩（POST /api/v1/data-intelligence/feedback——现有自评机制纯观测写 KgFeedbackLog）。
 * antd Typografy.copyable 不适用（需自定义五钮形态），直接实现。
 */
import React, { useState } from 'react';
import { Button, message as antdMessage } from 'antd';
import {
  CopyOutlined, BookOutlined, DownloadOutlined,
  LikeOutlined, DislikeOutlined, LikeFilled, DislikeFilled,
} from '@ant-design/icons';
import SaveToNotebookModal, { type NotebookSavePayload } from '../notebook/SaveToNotebookModal';

const BTN_STYLE: React.CSSProperties = {
  border: 'none', boxShadow: 'none', padding: '0 6px', height: 24,
  color: 'var(--text-tertiary)', fontSize: 12,
};

const MessageActions: React.FC<{
  /** AI 回答 Markdown 原文（复制/下载/存笔记共用） */
  text: string;
  /** 触发本回答的用户问题（存笔记 userQuery） */
  userQuery?: string;
  /** 消息 id（feedback message_id） */
  msgId?: string;
  /** 数据探索 run 标识（feedback run_id——缺省用 msgId，纯观测键） */
  runId?: string;
  testId?: string;
}> = ({ text, userQuery, msgId, runId, testId = 'msg-actions' }) => {
  const [saveOpen, setSaveOpen] = useState(false);
  const [verdict, setVerdict] = useState<'up' | 'down' | null>(null);

  const doCopy = async () => {
    try {
      await navigator.clipboard.writeText(text || '');
      antdMessage.success('已复制');
    } catch {
      antdMessage.error('复制失败');
    }
  };

  const doDownload = () => {
    try {
      const blob = new Blob([text || ''], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `answer-${(msgId || Date.now().toString()).replace(/[^\w-]/g, '')}.md`;
      a.click();
      URL.revokeObjectURL(url);
      antdMessage.success('已下载 Markdown');
    } catch {
      antdMessage.error('下载失败');
    }
  };

  const doVerdict = async (v: 'up' | 'down') => {
    setVerdict(v);
    try {
      await fetch('/api/v1/data-intelligence/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId || msgId || '', message_id: msgId, verdict: v }),
      });
      antdMessage.success(v === 'up' ? '已点赞，感谢反馈' : '已点踩，感谢反馈');
    } catch {
      antdMessage.warning('反馈提交失败（本地已记录）');
    }
  };

  const savePayload: NotebookSavePayload = {
    recordType: 'chat',
    title: (userQuery || '').trim().slice(0, 80) || '对话回答',
    userQuery: userQuery || '',
    output: text || '',
    metadata: { source: 'chat' },
  };

  return (
    <div
      data-testid={testId}
      className="msg-actions"
      style={{ display: 'flex', alignItems: 'center', gap: 2, marginTop: 4 }}
    >
      <Button size="small" type="text" icon={<CopyOutlined />} style={BTN_STYLE}
              onClick={doCopy} aria-label="复制" title="复制">复制</Button>
      <Button size="small" type="text" icon={<BookOutlined />} style={BTN_STYLE}
              onClick={() => setSaveOpen(true)} aria-label="保存到笔记" title="保存到笔记">保存到笔记</Button>
      <Button size="small" type="text" icon={<DownloadOutlined />} style={BTN_STYLE}
              onClick={doDownload} aria-label="下载 Markdown" title="下载 Markdown">下载</Button>
      <Button size="small" type="text"
              icon={verdict === 'up' ? <LikeFilled style={{ color: 'var(--color-primary)' }} /> : <LikeOutlined />}
              style={BTN_STYLE} onClick={() => doVerdict('up')} aria-label="点赞" title="点赞" />
      <Button size="small" type="text"
              icon={verdict === 'down' ? <DislikeFilled style={{ color: 'var(--color-error)' }} /> : <DislikeOutlined />}
              style={BTN_STYLE} onClick={() => doVerdict('down')} aria-label="点踩" title="点踩" />
      <SaveToNotebookModal
        open={saveOpen}
        payload={savePayload}
        onClose={() => setSaveOpen(false)}
        onSaved={() => antdMessage.success('已保存到笔记')}
      />
    </div>
  );
};

export default MessageActions;
