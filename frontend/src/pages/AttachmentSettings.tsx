/**
 * AttachmentSettings - 对话附件上限设置（批10 F3 最小补件）。
 * 原仓 (utility)/settings/attachments/page.tsx 语义承接：GET/PUT /api/v1/settings/chat-attachments
 * 四限值（max_file_mb/max_total_mb/max_chars_per_doc/max_chars_total）+ effective 生效值展示。
 * 端点面 1:1（settings 路由批10 vendor 挂载）；UI 按平台补最小件口径收敛为单卡。
 */
import React, { useEffect, useState } from 'react';
import { Button, Card, InputNumber, message, Space, Tag, Typography } from 'antd';
import { ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import { PageShell } from '../components/shell';

interface AttachmentLimits {
  max_file_mb: number;
  max_total_mb: number;
  max_chars_per_doc: number;
  max_chars_total: number;
}

const FIELDS: { key: keyof AttachmentLimits; label: string; hint: string }[] = [
  { key: 'max_file_mb', label: '单文件上限 (MB)', hint: '单个附件文件体积上限' },
  { key: 'max_total_mb', label: '总计上限 (MB)', hint: '单条消息附件总体积上限' },
  { key: 'max_chars_per_doc', label: '单文档字符上限', hint: '单个文档解析入上下文的字符数上限' },
  { key: 'max_chars_total', label: '总字符上限', hint: '单条消息附件解析总字符上限' },
];

const AttachmentSettings: React.FC = () => {
  const [limits, setLimits] = useState<AttachmentLimits | null>(null);
  const [effective, setEffective] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/v1/settings/chat-attachments');
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      setLimits(d.settings ?? null);
      setEffective(d.effective ?? null);
    } catch {
      message.error('读取附件设置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!limits) return;
    setSaving(true);
    try {
      const r = await fetch('/api/v1/settings/chat-attachments', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: limits }),
      });
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      setLimits(d.settings ?? limits);
      setEffective(d.effective ?? null);
      message.success('附件上限已保存');
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell title="对话附件上限" description="聊天附件体积/字符限额（chat-attachments，admin-only）">
      <Card
        size="small"
        title="限额设置"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={save} loading={saving} disabled={!limits}>保存</Button>
          </Space>
        }
        style={{ maxWidth: 720 }}
      >
        {limits ? (
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            {FIELDS.map((f) => (
              <Space key={f.key} style={{ width: '100%', justifyContent: 'space-between' }}>
                <div>
                  <div>{f.label}</div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{f.hint}</Typography.Text>
                </div>
                <InputNumber
                  min={0}
                  value={limits[f.key]}
                  onChange={(v) => setLimits({ ...limits, [f.key]: Number(v) || 0 })}
                  style={{ width: 160 }}
                />
              </Space>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">{loading ? '加载中…' : '暂无设置'}</Typography.Text>
        )}
      </Card>
      {effective ? (
        <Card size="small" title="生效值（effective）" style={{ maxWidth: 720, marginTop: 12 }}>
          <Space wrap>
            {Object.entries(effective).map(([k, v]) => (
              <Tag key={k}>{k}: {String(v)}</Tag>
            ))}
          </Space>
        </Card>
      ) : null}
    </PageShell>
  );
};

export default AttachmentSettings;
