/**
 * ⑤批4（⑤e §一）：练习页 /e/tutor/practice——知识点+难度三档→POST /api/tutor/practice
 * （agent run surface=quiz，SSE 流式回判分）。UI 处理流式中间态（⑤e 诚实账②）。
 */
import React, { useRef, useState } from 'react';
import { Button, Card, Input, Radio, Space, message } from 'antd';

const { TextArea } = Input;

const TutorPractice: React.FC = () => {
  const [knowledgePoint, setKnowledgePoint] = useState('');
  const [band, setBand] = useState<string>('基础');
  const [streamText, setStreamText] = useState('');
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const startPractice = async () => {
    if (!knowledgePoint.trim()) {
      message.warning('先填知识点（如：变压器）');
      return;
    }
    setRunning(true);
    setStreamText('');
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const r = await fetch('/api/tutor/practice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: `出题练习：知识点「${knowledgePoint}」，难度「${band}」。请出题并等待我作答。` }),
        signal: ctrl.signal,
      });
      if (!r.ok || !r.body) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j?.detail || `HTTP ${r.status}`);
      }
      // SSE 逐段解析（event:/data: 帧——与后端 freeplan 流协议一致）
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop() || '';
        for (const frame of parts) {
          const dataLine = frame.split('\n').find((l) => l.startsWith('data: '));
          if (!dataLine) continue;
          try {
            const evt = JSON.parse(dataLine.slice(6));
            const txt = evt?.text || evt?.phase_text || evt?.token || '';
            if (txt) setStreamText((prev) => prev + txt);
            if (evt?.message_card?.content) setStreamText((prev) => prev + evt.message_card.content);
          } catch { /* 非 JSON 帧（心跳）忽略 */ }
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') message.error(e?.message || '练习请求失败');
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  };

  return (
    <Card title="练习" style={{ margin: 16 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Space wrap>
          <Input
            style={{ width: 320 }}
            placeholder="知识点（如：变压器）"
            value={knowledgePoint}
            onChange={(e) => setKnowledgePoint(e.target.value)}
          />
          <Radio.Group value={band} onChange={(e) => setBand(e.target.value)}>
            <Radio.Button value="基础">基础</Radio.Button>
            <Radio.Button value="提高">提高</Radio.Button>
            <Radio.Button value="挑战">挑战</Radio.Button>
          </Radio.Group>
          <Button type="primary" loading={running} onClick={startPractice}>
            {running ? '出题中…' : '开始练习'}
          </Button>
          {running && <Button danger onClick={() => abortRef.current?.abort()}>停止</Button>}
        </Space>
        <TextArea
          readOnly
          rows={16}
          placeholder="出题与判分结果（流式）"
          value={streamText}
        />
      </Space>
    </Card>
  );
};

export default TutorPractice;
