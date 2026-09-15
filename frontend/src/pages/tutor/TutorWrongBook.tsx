/**
 * ⑤批4（⑤e）：错题本基页 + ⑤补补-5 步骤 5/6 扩面——
 * 录入按钮（表单：题干/选项/正确答案/我的答案/知识点/母题搜索关联或新建/错因——source=manual）+
 * 管理面（筛选：状态/错因/来源；详情抽屉：完整题结构+编辑+状态流转 open→resolved+删除软删）+
 * 错因分析卡片（analyze_wrong_questions 聚合）+联动（举一反三→练习页/进复习→复习页/导出）。
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Drawer, Empty, Form, Input, List, Modal, Segmented, Select, Space, Tag, message,
} from 'antd';
import { useNavigate } from 'react-router-dom';

interface WrongItem {
  wq_id: string;
  mother_question_id: string;
  variant_text: string;
  error_context: string;
  status: string;
  wrong_at: string;
  resolved_at: string | null;
  question: { stem?: string; options?: string[]; correct_answer?: string } | null;
  my_answer: string;
  error_type: string;
  source: string;
  mother_kp: string;
}
interface Analysis { total: number; error_type_distribution: Record<string, { count: number; ratio: number }>; conclusion: string }

const ERROR_TYPE_LABEL: Record<string, string> = {
  concept: '概念不清', careless: '粗心失误', technique: '技巧欠缺', unclassified: '未分类',
};

const TutorWrongBook: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<WrongItem[]>([]);
  const [status, setStatus] = useState<string>('open');
  const [errorType, setErrorType] = useState<string>('');
  const [source, setSource] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [current, setCurrent] = useState<WrongItem | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async (st: string, et: string, src: string) => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ status: st, error_type: et, source: src, page_size: '100' });
      const r = await fetch(`/api/tutor/wrong-questions?${qs.toString()}`);
      const j = await r.json();
      setItems(j?.data?.items || []);
    } catch {
      message.error('错题列表获取失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAnalysis = useCallback(async () => {
    try {
      const r = await fetch('/api/tutor/analyze-wrong-questions');
      const j = await r.json();
      setAnalysis(j?.data || null);
    } catch { /* 分析失败静默——卡片回落 */ }
  }, []);

  useEffect(() => { load(status, errorType, source); }, [load, status, errorType, source]);
  useEffect(() => { loadAnalysis(); }, [loadAnalysis]);

  const exportBook = async () => {
    try {
      const r = await fetch('/api/tutor/wrong-questions?status=&page_size=100');
      const j = await r.json();
      const all: WrongItem[] = j?.data?.items || [];
      const lines = ['# 错题本（前端导出）', ''];
      all.forEach((x) => {
        lines.push(`- [${x.status}] ${x.variant_text}`);
        if (x.error_context) lines.push(`  - 上下文: ${x.error_context}`);
        if (x.error_type) lines.push(`  - 错因: ${ERROR_TYPE_LABEL[x.error_type] || x.error_type}`);
      });
      const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'wrongbook.md';
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${all.length} 条`);
    } catch {
      message.error('导出失败');
    }
  };

  const submitCreate = async (v: any) => {
    try {
      const r = await fetch('/api/tutor/wrong-questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stem: v.stem, options: (v.options || '').split('\n').filter((s: string) => s.trim()),
          correct_answer: v.correct_answer || '', my_answer: v.my_answer || '',
          knowledge_point_id: v.knowledge_point_id || '',
          mother_keywords: v.mother_keywords || v.stem?.slice(0, 20) || '',
          error_type: v.error_type || '',
        }),
      });
      const j = await r.json();
      if (r.status !== 200) { message.error(j?.detail || '录入失败'); return; }
      message.success(`已录入（wq_id=${j.data?.wq_id?.slice(0, 8)}…，source=manual）`);
      setFormOpen(false);
      form.resetFields();
      load(status, errorType, source);
    } catch {
      message.error('录入失败');
    }
  };

  const setStatusOf = async (wqId: string, st: string) => {
    const r = await fetch(`/api/tutor/wrong-questions/${wqId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: st }),
    });
    if (r.status === 200) {
      message.success(st === 'resolved' ? '已标记解决' : '已重开');
      load(status, errorType, source);
      setCurrent(null);
    } else {
      message.error('状态更新失败');
    }
  };

  const deleteOne = async (wqId: string) => {
    const r = await fetch(`/api/tutor/wrong-questions/${wqId}`, { method: 'DELETE' });
    if (r.status === 200) {
      message.success('已删除（软删，可追溯）');
      load(status, errorType, source);
      setCurrent(null);
    } else {
      message.error('删除失败');
    }
  };

  return (
    <div style={{ margin: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card
        title="错题本"
        extra={(
          <Space wrap>
            <Segmented
              value={status}
              onChange={(v) => setStatus(v as string)}
              options={[{ label: '未解决', value: 'open' }, { label: '已解决', value: 'resolved' }, { label: '全部', value: '' }]}
            />
            <Select
              allowClear placeholder="错因" style={{ minWidth: 110 }} value={errorType || undefined}
              onChange={(v) => setErrorType(v || '')}
              options={Object.entries(ERROR_TYPE_LABEL).map(([k, l]) => ({ value: k, label: l }))}
            />
            <Select
              allowClear placeholder="来源" style={{ minWidth: 96 }} value={source || undefined}
              onChange={(v) => setSource(v || '')}
              options={[{ value: 'chat', label: '对话' }, { value: 'manual', label: '手动' }, { value: 'practice', label: '练习' }]}
            />
            <Button type="primary" onClick={() => setFormOpen(true)}>录入</Button>
            <Button onClick={exportBook}>导出</Button>
          </Space>
        )}
        style={{ borderRadius: 12 }}
      >
        <List
          loading={loading}
          dataSource={items}
          locale={{ emptyText: <Empty description="没有错题，继续保持" /> }}
          renderItem={(item) => (
            <List.Item onClick={() => setCurrent(item)} style={{ cursor: 'pointer' }}>
              <List.Item.Meta
                title={(
                  <Space wrap>
                    <span>{item.variant_text}</span>
                    <Tag color={item.status === 'open' ? 'red' : 'green'}>{item.status === 'open' ? '未解决' : '已解决'}</Tag>
                    {item.error_type && <Tag>{ERROR_TYPE_LABEL[item.error_type] || item.error_type}</Tag>}
                    {item.source && <Tag>{item.source === 'chat' ? '对话' : item.source === 'manual' ? '手动' : '练习'}</Tag>}
                  </Space>
                )}
                description={item.mother_question_id ? `关联母题: ${item.mother_question_id}` : undefined}
              />
            </List.Item>
          )}
        />
      </Card>

      <Card title="错因分析（analyze_wrong_questions 聚合）" size="small" style={{ borderRadius: 12 }}>
        {!analysis || analysis.total === 0 ? (
          <span style={{ color: 'var(--text-tertiary)' }}>暂无错题记录。</span>
        ) : (
          <div>
            <div style={{ marginBottom: 6 }}>
              {Object.entries(analysis.error_type_distribution).map(([k, v]) => (
                <Tag key={k} color={k === 'concept' ? 'red' : k === 'careless' ? 'orange' : 'blue'}>
                  {ERROR_TYPE_LABEL[k] || k} {v.count} 条（{Math.round(v.ratio * 100)}%）
                </Tag>
              ))}
            </div>
            <span style={{ fontSize: 13 }}>{analysis.conclusion}</span>
          </div>
        )}
      </Card>

      <Drawer
        title="错题详情"
        open={!!current}
        onClose={() => setCurrent(null)}
        width={520}
        extra={current && (
          <Space>
            {current.status === 'open' && (
              <Button size="small" type="primary" onClick={() => setStatusOf(current.wq_id, 'resolved')}>标为已解决</Button>
            )}
            <Button size="small" danger onClick={() => deleteOne(current.wq_id)}>删除</Button>
          </Space>
        )}
      >
        {current && (
          <Space direction="vertical" style={{ width: '100%' }} size={10}>
            <div><b>题面：</b>{current.question?.stem || current.variant_text}</div>
            {current.question?.options && current.question.options.length > 0 && (
              <div><b>选项：</b>{current.question.options.join(' / ')}</div>
            )}
            {current.question?.correct_answer && <div><b>正确答案：</b>{current.question.correct_answer}</div>}
            {current.my_answer && <div><b>我的答案：</b>{current.my_answer}</div>}
            {current.error_context && <div><b>错误上下文：</b>{current.error_context}</div>}
            <div>
              <b>状态：</b>
              <Tag color={current.status === 'open' ? 'red' : 'green'}>{current.status}</Tag>
              {current.error_type && <Tag>{ERROR_TYPE_LABEL[current.error_type] || current.error_type}</Tag>}
              {current.source && <Tag>{current.source === 'chat' ? '对话' : current.source === 'manual' ? '手动' : '练习'}</Tag>}
            </div>
            <div><b>记录时间：</b>{current.wrong_at}</div>
            {current.mother_question_id && <div><b>关联母题：</b>{current.mother_question_id}</div>}
            {current.mother_kp && <div><b>知识点：</b>{current.mother_kp}</div>}
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Button size="small" onClick={() => navigate('/e/tutor/practice')}>举一反三（同知识点练习）</Button>
              <Button size="small" onClick={() => navigate('/e/tutor/review')}>进复习（FSRS 卡）</Button>
            </div>
          </Space>
        )}
      </Drawer>

      <Modal
        title="录入错题（source=manual）"
        open={formOpen}
        onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()}
        okText="落库"
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={submitCreate}>
          <Form.Item name="stem" label="题干" rules={[{ required: true, message: '题干必填' }]}>
            <Input.TextArea rows={2} placeholder="完整题面" />
          </Form.Item>
          <Form.Item name="options" label="选项（每行一个，选填）">
            <Input.TextArea rows={2} placeholder={'A. 选项一\nB. 选项二'} />
          </Form.Item>
          <Form.Item name="correct_answer" label="正确答案">
            <Input placeholder="如：B" />
          </Form.Item>
          <Form.Item name="my_answer" label="我的答案">
            <Input placeholder="当时填了什么" />
          </Form.Item>
          <Form.Item name="knowledge_point_id" label="知识点（图谱节点 code，如 kp:有理数）">
            <Input placeholder="kp:…" />
          </Form.Item>
          <Form.Item name="mother_keywords" label="母题关键词（留空则按题干自动搜/建）">
            <Input placeholder="如：有理数分类" />
          </Form.Item>
          <Form.Item name="error_type" label="错因">
            <Select
              allowClear placeholder="选错因（可后改）"
              options={Object.entries(ERROR_TYPE_LABEL).filter(([k]) => k !== 'unclassified').map(([k, l]) => ({ value: k, label: l }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TutorWrongBook;
