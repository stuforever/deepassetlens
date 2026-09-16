/**
 * 母题导出弹窗——1:1 移植自原仓 web/components/mother-questions/ExportModal.tsx
 * （Next.js+Tailwind → React+antd；API 契约/文案/交互逐字保留，i18n key 直出中文）。
 * 导出：POST /api/v1/mother-questions/export，按 Content-Disposition 解析文件名下载 docx。
 */
import { useState } from 'react';
import type { CSSProperties } from 'react';
import { Button, Checkbox, Input, InputNumber, Modal, Radio, Select, message } from 'antd';
import { CloseOutlined, DownloadOutlined, LoadingOutlined } from '@ant-design/icons';
import { SUBJECTS, SUBJECT_DISPLAY } from './dtFields';

interface ExportModalProps {
  onClose: () => void;
  /** 当前列表中的题目 ID（用于"导出当前列表"） */
  currentIds?: string[];
}

const labelStyle: CSSProperties = { fontSize: 12, color: 'rgba(0,0,0,0.45)' };
const dateInputStyle: CSSProperties = {
  flex: 1, padding: '4px 11px', fontSize: 14, border: '1px solid #d9d9d9',
  borderRadius: 6, background: '#fff', color: 'inherit',
};
const DIFF_OPTIONS = [1, 2, 3, 4, 5].map((n) => ({ value: n, label: `${'★'.repeat(n)} (${n})` }));

export function ExportModal({ onClose, currentIds = [] }: ExportModalProps) {
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [minDiff, setMinDiff] = useState(1);
  const [maxDiff, setMaxDiff] = useState(5);
  const [limit, setLimit] = useState(50);
  const [withAnswer, setWithAnswer] = useState(true);
  const [withImage, setWithImage] = useState(true);
  const [withWrongImage, setWithWrongImage] = useState(false);
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');
  const [onlyCurrentList, setOnlyCurrentList] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const payload: Record<string, any> = {
        subject: onlyCurrentList ? '' : subject,
        min_difficulty: minDiff,
        max_difficulty: maxDiff,
        limit: onlyCurrentList ? currentIds.length : limit,
        with_answer: withAnswer,
        with_image: withImage,
        with_wrong_image: withWrongImage,
        title,
        date_start: dateStart,
        date_end: dateEnd,
        ids: onlyCurrentList ? currentIds : [],
      };
      const res = await fetch('/api/v1/mother-questions/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        message.error(`导出失败: ${err.detail || res.statusText}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cd = res.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename\*=UTF-8''([^;]+)/) || cd.match(/filename=([^;]+)/);
      a.download = match ? decodeURIComponent(match[1]) : '母题组卷.docx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      message.success('导出成功');
      onClose();
    } catch (e) {
      message.error(`导出异常: ${(e as Error).message}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Modal
      open
      onCancel={onClose}
      width={448}
      data-testid="mq-export-modal"
      closeIcon={<CloseOutlined data-testid="mq-export-close" />}
      title={(
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, lineHeight: '28px' }}>导出母题组卷</div>
          <div style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)', marginTop: 2 }}>生成 Word 文档，可直接打印</div>
        </div>
      )}
      footer={(
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={onClose} data-testid="mq-export-cancel">取消</Button>
          <Button
            type="primary"
            onClick={handleExport}
            disabled={exporting}
            data-testid="mq-export-docx"
            icon={exporting ? <LoadingOutlined /> : <DownloadOutlined />}
          >
            {exporting ? '导出中...' : '导出 DOCX'}
          </Button>
        </div>
      )}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxHeight: '70vh', overflowY: 'auto' }}>
        {/* 试卷标题 */}
        <div>
          <label style={labelStyle}>试卷标题（可选）</label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="留空将自动生成"
            style={{ marginTop: 4 }}
            data-testid="mq-export-title"
          />
        </div>

        {/* 选题范围 */}
        <div>
          <label style={labelStyle}>选题范围</label>
          <div style={{ marginTop: 4 }}>
            <Radio.Group value={onlyCurrentList} onChange={(e) => setOnlyCurrentList(!!e.target.value)}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <Radio value={false} data-testid="mq-export-scope-all">按筛选条件导出全部</Radio>
                {currentIds.length > 0 && (
                  <Radio value={true} data-testid="mq-export-scope-current">导出当前列表（{currentIds.length}题）</Radio>
                )}
              </div>
            </Radio.Group>
          </div>
        </div>

        {/* 学科 */}
        {!onlyCurrentList && (
          <div>
            <label style={labelStyle}>科目</label>
            <Select
              value={subject}
              onChange={(v) => setSubject(v)}
              style={{ width: '100%', marginTop: 4 }}
              data-testid="mq-export-subject"
              options={[
                { value: '', label: '全部' },
                ...Object.entries(SUBJECTS).map(([k]) => ({ value: k, label: SUBJECT_DISPLAY[k] })),
              ]}
            />
          </div>
        )}

        {/* 难度范围 */}
        {!onlyCurrentList && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>最小难度</label>
              <Select
                value={minDiff}
                onChange={(v) => setMinDiff(Number(v))}
                style={{ width: '100%', marginTop: 4 }}
                data-testid="mq-export-min-diff"
                options={DIFF_OPTIONS}
              />
            </div>
            <div>
              <label style={labelStyle}>最大难度</label>
              <Select
                value={maxDiff}
                onChange={(v) => setMaxDiff(Number(v))}
                style={{ width: '100%', marginTop: 4 }}
                data-testid="mq-export-max-diff"
                options={DIFF_OPTIONS}
              />
            </div>
          </div>
        )}

        {/* 题量上限 */}
        {!onlyCurrentList && (
          <div>
            <label style={labelStyle}>题量上限</label>
            <InputNumber
              min={1}
              max={200}
              value={limit}
              onChange={(v) => setLimit(typeof v === 'number' ? v : 50)}
              style={{ width: '100%', marginTop: 4 }}
              data-testid="mq-export-limit"
            />
          </div>
        )}

        {/* 日期范围 */}
        {!onlyCurrentList && (
          <div>
            <label style={labelStyle}>按录入时间筛选（可选）</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 4 }}>
              <input
                type="date"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                style={dateInputStyle}
                data-testid="mq-export-date-start"
              />
              <input
                type="date"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                style={dateInputStyle}
                data-testid="mq-export-date-end"
              />
            </div>
          </div>
        )}

        {/* 试卷模式 */}
        <div>
          <label style={labelStyle}>试卷模式</label>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <Button
              block
              type={withAnswer ? 'primary' : 'default'}
              onClick={() => setWithAnswer(true)}
              data-testid="mq-export-teacher"
              data-active={withAnswer ? 'true' : 'false'}
            >
              📚 教师版（带答案）
            </Button>
            <Button
              block
              type={!withAnswer ? 'primary' : 'default'}
              onClick={() => setWithAnswer(false)}
              data-testid="mq-export-student"
              data-active={!withAnswer ? 'true' : 'false'}
            >
              ✏️ 学生版（练习用）
            </Button>
          </div>
        </div>

        {/* 图片选项 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Checkbox
            checked={withImage}
            onChange={(e) => setWithImage(e.target.checked)}
            data-testid="mq-export-with-image"
          >
            包含题目图片
          </Checkbox>
          <Checkbox
            checked={withWrongImage}
            onChange={(e) => setWithWrongImage(e.target.checked)}
            data-testid="mq-export-with-wrong-image"
          >
            包含错误答案截图
          </Checkbox>
        </div>
      </div>
    </Modal>
  );
}

export default ExportModal;
