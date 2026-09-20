/**
 * 录题页（新增母题）——1:1 移植自原仓 web/app/(workspace)/mother-questions/new/page.tsx
 * （Next.js+Tailwind → React+react-router+antd；顶部栏/表单/409 强制创建流程逐字保留，
 * i18n key 直出中文）。表单字段组件为同目录 MotherQuestionForm.tsx 的 MotherQuestionFields。
 * API 契约：POST /api/v1/mother-questions（409 → force:true 二次提交）。
 */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, message } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { MotherQuestionFields } from './MotherQuestionForm';
import { toFormData, buildPayload, type MotherQuestionData } from './dtFields';

function NewQuestionContent() {
  const navigate = useNavigate();
  const searchParams = useSearchParams()[0];
  const photoMode = searchParams.get('photo') === '1';
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<MotherQuestionData>(toFormData({}));

  const onChange = (patch: Partial<MotherQuestionData>) => setForm((f) => ({ ...f, ...patch }));

  const onSave = async () => {
    if (!form.title || !form.question_text) {
      message.error('标题和题干必填');
      return;
    }
    setSaving(true);
    try {
      const payload = buildPayload(form);
      const res = await fetch('/api/v1/mother-questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (res.status === 409) {
          if (window.confirm(err.detail + '\n\n' + '确认仍要创建？')) {
            const res2 = await fetch('/api/v1/mother-questions', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ...payload, force: true }),
            });
            if (!res2.ok) throw new Error();
            const data2 = await res2.json();
            message.success('母题已创建');
            navigate(`/e/sishu/admin/mother-questions/${data2.id}`);
            return;
          }
          setSaving(false);
          return;
        }
        throw new Error();
      }
      const data = await res.json();
      message.success('母题已创建');
      navigate(`/e/sishu/admin/mother-questions/${data.id}`);
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ height: '100%', overflowY: 'auto', background: '#fff' }} data-testid="mq-new-page">
      {/* 顶部栏 */}
      <div style={{ position: 'sticky', top: 0, zIndex: 40, background: '#fff', borderBottom: '1px solid #d9d9d9', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button type="text" onClick={() => navigate('/e/sishu/admin/mother-questions')} icon={<ArrowLeftOutlined style={{ fontSize: 20 }} />} data-testid="mq-back-btn" />
          <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0 }} data-testid="mq-new-title">{photoMode ? '拍照录入母题' : '新增母题'}</h1>
        </div>
        <Button
          onClick={onSave}
          loading={saving}
          type="primary"
          data-testid="mq-save-btn"
          icon={<SaveOutlined />}
        >
          保存
        </Button>
      </div>

      {/* 表单区域 */}
      <div style={{ maxWidth: 768, margin: '0 auto', padding: 24 }}>
        <MotherQuestionFields
          value={form}
          onChange={onChange}
          photoMode={photoMode}
          showClassification={true}
        />
      </div>
    </div>
  );
}

export default function NewQuestionPage() {
  return <NewQuestionContent />;
}
