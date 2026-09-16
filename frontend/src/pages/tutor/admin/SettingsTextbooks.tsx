/**
 * 课本管理（1:1 复刻自原仓 web/app/(utility)/settings/curriculum/textbooks/page.tsx）：
 * 教材列表（页数/章数统计、PDF 上传拆页、删除）+ 新增教材表单。
 * next/link → 合页后切 tab；notify → antd message；Tailwind → antd + 内联样式。
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Col, Input, Row, Select, message } from 'antd';
import {
  BookOutlined, DeleteOutlined, FileAddOutlined, FileTextOutlined,
  LoadingOutlined, PlusOutlined, UploadOutlined,
} from '@ant-design/icons';
import { SettingsPageHeader } from './SettingsPageHeader';
import { useCurriculumTab } from './dtCurriculumTab';

const SUBJECTS: [string, string][] = [
  ['math', '数学'],
  ['chinese', '语文'],
  ['english', '英语'],
  ['science', '科学'],
  ['physics', '物理'],
  ['chemistry', '化学'],
  ['biology', '生物'],
  ['history', '历史'],
  ['geography', '地理'],
];
const GRADES = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级', '七年级', '八年级', '九年级'];

interface Textbook {
  id: string;
  name: string;
  subject: string;
  grade: string | null;
  version: string | null;
  create_time?: number;
}

const cardStyle: React.CSSProperties = { border: '1px solid #f0f0f0', borderRadius: 8, background: '#fff' };

export default function SettingsTextbooks() {
  const [items, setItems] = useState<Textbook[]>([]);
  const [pageCount, setPageCount] = useState<Record<string, number>>({});
  const [chapterCount, setChapterCount] = useState<Record<string, number>>({});
  const [importing, setImporting] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [grade, setGrade] = useState('七年级');
  const [subject, setSubject] = useState('math');
  const [version, setVersion] = useState('');
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const { goToTab } = useCurriculumTab();

  const load = useCallback(async () => {
    const d = await fetch('/api/v1/curriculum/textbooks').then((r) => r.json());
    const list: Textbook[] = d.items || [];
    setItems(list);
    const pc: Record<string, number> = {};
    const cc: Record<string, number> = {};
    await Promise.all(
      list.map(async (t) => {
        try {
          const [p, ch] = await Promise.all([
            fetch(`/api/v1/curriculum/textbooks/${t.id}/pages`).then((r) => r.json()),
            fetch(`/api/v1/curriculum/textbooks/${t.id}/chapters`).then((r) => r.json()),
          ]);
          pc[t.id] = (p.items || []).length;
          cc[t.id] = (ch.items || []).length;
        } catch {
          pc[t.id] = 0;
          cc[t.id] = 0;
        }
      }),
    );
    setPageCount(pc);
    setChapterCount(cc);
  }, []);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const add = async () => {
    if (!name) {
      message.error('名称必填');
      return;
    }
    await fetch('/api/v1/curriculum/textbooks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, grade, subject, version: version || null }),
    });
    setName('');
    setVersion('');
    message.success('已添加');
    load();
  };

  const del = async (id: string) => {
    if (!confirm('删除此教材及其章节？')) return;
    await fetch(`/api/v1/curriculum/textbooks/${id}`, { method: 'DELETE' });
    message.success('已删除');
    load();
  };

  const importPdf = async (id: string, file: File | undefined) => {
    if (!file) return;
    setImporting(id);
    message.info(`正在解析 PDF（${file.name}）...`);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await fetch(`/api/v1/curriculum/textbooks/${id}/import`, {
        method: 'POST',
        body: form,
      });
      if (!r.ok) {
        const e = await r.text();
        message.error(`导入失败: ${e.slice(0, 120)}`);
      } else {
        const d = await r.json();
        message.success(`已导入 ${d.page_count} 页`);
        load();
      }
    } catch (e) {
      message.error('导入请求失败');
    }
    setImporting(null);
  };

  const linkStyle = { color: '#1677ff', cursor: 'pointer' } as React.CSSProperties;

  return (
    <div>
      <SettingsPageHeader
        title="课本管理"
        description="教材是课程体系的源头：先添加教材，再上传 PDF 拆页成图；随后在「章节管理」按教材建立章节（设页码），最后在「章节/知识点」里建立与知识点的关联。"
      />
      <div
        style={{
          marginBottom: 16, borderRadius: 8, border: '1px solid #f0f0f0',
          background: 'rgba(0,0,0,0.02)', padding: 12, fontSize: 13, color: 'rgba(0,0,0,0.45)',
        }}
      >
        流转路径：<span style={{ color: '#1677ff' }}>教材</span> → 上传 PDF（拆页成图）→{' '}
        <a style={linkStyle} onClick={() => goToTab('chapters')}>
          章节管理
        </a>
        （建章设页码，权威源）→{' '}
        <a style={linkStyle} onClick={() => goToTab('knowledge-points')}>
          知识点管理
        </a>
        （提炼与关联）。自主学习章节来源于此，保持一致。
      </div>

      <Row gutter={20}>
        {/* 教材列表 */}
        <Col xs={24} lg={12}>
          <section style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
              <BookOutlined style={{ color: '#0ea5e9' }} />
              <h2 style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>教材列表</h2>
              <span style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', marginLeft: 'auto' }}>{items.length} 本</span>
            </div>
            <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '65vh', overflowY: 'auto' }}>
              {items.length === 0 ? (
                <p style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>暂无教材，先在右侧添加。</p>
              ) : (
                items.map((t) => (
                  <div key={t.id} style={{ borderRadius: 8, border: '1px solid #f0f0f0', padding: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 500, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.name}</div>
                        <div style={{ marginTop: 2, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6, fontSize: 11, color: 'rgba(0,0,0,0.45)' }}>
                          <span style={{ padding: '1px 6px', borderRadius: 4, background: '#f5f5f5' }}>
                            {SUBJECTS.find(([v]) => v === t.subject)?.[1] || t.subject}
                          </span>
                          {t.grade && <span>{t.grade}</span>}
                          {t.version && <span>· {t.version}</span>}
                          <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                              <FileTextOutlined style={{ fontSize: 12 }} />
                              {pageCount[t.id] ?? '–'}页
                            </span>
                            <span>· {chapterCount[t.id] ?? '–'}章</span>
                          </span>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                        <Button
                          size="small"
                          icon={importing === t.id ? <LoadingOutlined spin /> : <UploadOutlined />}
                          onClick={() => fileRefs.current[t.id]?.click()}
                          disabled={importing === t.id}
                          title="上传 PDF（拆页成图 + OCR）"
                        >
                          上传PDF
                        </Button>
                        <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => del(t.id)} />
                      </div>
                    </div>
                    <input
                      ref={(el) => {
                        fileRefs.current[t.id] = el;
                      }}
                      type="file"
                      accept="application/pdf"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        importPdf(t.id, e.target.files?.[0]);
                        e.target.value = '';
                      }}
                    />
                  </div>
                ))
              )}
            </div>
          </section>
        </Col>

        {/* 新增教材 */}
        <Col xs={24} lg={12}>
          <section style={{ ...cardStyle, alignSelf: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
              <PlusOutlined style={{ color: '#0ea5e9' }} />
              <h2 style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>新增教材</h2>
            </div>
            <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Input
                placeholder="教材名称（如 人教版 七年级上册 数学）"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <Select
                  value={grade}
                  onChange={(v) => setGrade(v)}
                  options={GRADES.map((g) => ({ value: g, label: g }))}
                />
                <Select
                  value={subject}
                  onChange={(v) => setSubject(v)}
                  options={SUBJECTS.map(([v, l]) => ({ value: v, label: l }))}
                />
              </div>
              <Input
                placeholder="版本（如 人教版 / 北师大版 / 外研社）"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
              />
              <div>
                <Button type="primary" icon={<FileAddOutlined />} onClick={add}>
                  添加
                </Button>
              </div>
            </div>
          </section>
        </Col>
      </Row>
    </div>
  );
}
