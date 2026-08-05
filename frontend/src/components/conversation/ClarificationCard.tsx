/**
 * 澄清弹窗 - trae 风格
 *
 * 特性：
 *   1. 弹窗形式（Modal），不是内嵌卡片
 *   2. 多选用 Checkbox 列表，单选用 Radio 列表
 *   3. 选项卡片化：实体名 + 主表/联接表标签 + 属性数 + 属性预览
 *   4. 底部有「提交」按钮，选中后统一提交
 *   5. 支持手动补充输入
 */
import React, { useMemo, useState, useEffect } from 'react';
import { Modal, Button, Checkbox, Radio, Input, Space, Typography, Tag, Divider, Empty } from 'antd';
import type { ConversationCard, ConversationCardAction } from './types';
import { tokens } from '../../theme/tokens';
import { StatusTag } from '../shell';

const { Text, Paragraph } = Typography;

type ClarificationCardProps = {
  card: ConversationCard;
  disabled?: boolean;
  onAction?: (action: ConversationCardAction) => void;
};

const ClarificationCard: React.FC<ClarificationCardProps> = ({ card, disabled = false, onAction }) => {
  const [open, setOpen] = useState(true);
  const question = String(card.data?.question || card.summary || '');
  const hint = String(card.data?.hint || '');
  const options = useMemo(() => (Array.isArray(card.data?.options) ? card.data.options : []), [card.data?.options]);
  const multiSelect = Boolean(card.data?.multi_select);
  const manualAllowed = card.data?.manual_allowed !== false;
  const [selectedValues, setSelectedValues] = useState<string[]>([]);
  const [manualText, setManualText] = useState('');

  useEffect(() => {
    setOpen(true);
    setSelectedValues([]);
    setManualText('');
  }, [card.card_id]);

  const selectedOptions = useMemo(
    () => options.filter((item: any) => {
      const value = String(item?.value || item?.label || '');
      return value && selectedValues.includes(value);
    }),
    [options, selectedValues]
  );

  const handleSubmit = () => {
    const selectedTexts = selectedOptions.map((item: any) => String(item?.value || item?.label || '')).filter(Boolean);
    const manual = manualText.trim();
    const submitParts = [...selectedTexts, ...(manual ? [manual] : [])];
    const submitValue = submitParts.join('；').trim();
    if (!submitValue) return;
    onAction?.({
      action_type: 'submit_clarification',
      submit_value: submitValue,
      card,
      option: !multiSelect && selectedOptions.length === 1 ? selectedOptions[0] : undefined,
      selected_options: selectedOptions,
      manual_text: manual,
    });
    setOpen(false);
    setSelectedValues([]);
    setManualText('');
  };

  const handleCancel = () => {
    setOpen(false);
  };

  const canSubmit = selectedValues.length > 0 || manualText.trim().length > 0;

  const renderOption = (option: any, index: number) => {
    const label = String(option?.label || option?.value || option?.entity_name || '');
    const value = String(option?.value || option?.label || option?.entity_code || '');
    if (!label || !value) return null;
    const isMain = option?.is_main_table !== false;
    const attrCount = Array.isArray(option?.attributes) ? option.attributes.length : 0;
    const attrPreview = attrCount > 0
      ? (option.attributes.slice(0, 4).map((a: any) => a.attribute_name || a.name || a.attribute_code).filter(Boolean).join('、') + (attrCount > 4 ? ' 等' : ''))
      : '';
    const isSelected = selectedValues.includes(value);

    const optionNode = (
      <div
        key={`${value}-${index}`}
        onClick={() => {
          if (disabled) return;
          if (multiSelect) {
            setSelectedValues((prev) => prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]);
          } else {
            setSelectedValues([value]);
          }
        }}
        style={{
          padding: '8px 10px',
          borderRadius: 6,
          border: isSelected ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
          background: isSelected ? 'var(--color-primary-bg)' : 'var(--bg-subtle)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
        }}
      >
        <div style={{ flexShrink: 0, paddingTop: 2 }}>
          {multiSelect ? (
            <Checkbox checked={isSelected} disabled={disabled} />
          ) : (
            <Radio checked={isSelected} disabled={disabled} />
          )}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <Text strong style={{ fontSize: 13 }}>{label}</Text>
            <StatusTag preset={isMain ? 'info' : 'warning'} style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}>
              {isMain ? '主表' : '联接表'}
            </StatusTag>
            {attrCount > 0 ? (
              <Tag style={{ fontSize: 11, lineHeight: '16px', margin: 0, background: 'var(--color-border)', border: 'none' }}>
                {attrCount} 属性
              </Tag>
            ) : null}
          </div>
          {attrPreview ? (
            <div style={{ marginTop: 2 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{attrPreview}</Text>
            </div>
          ) : null}
          {option?.description ? (
            <div style={{ marginTop: 2 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{String(option.description)}</Text>
            </div>
          ) : null}
        </div>
      </div>
    );
    return optionNode;
  };

  return (
    <Modal
      open={open}
      onCancel={handleCancel}
      title={
        <Space>
          <StatusTag preset="warning">需要确认</StatusTag>
          <Text strong>{card.title || '补充信息'}</Text>
        </Space>
      }
      width={560}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {multiSelect ? `多选 · 已选 ${selectedValues.length} 项` : `单选 · 已选 ${selectedValues.length} 项`}
          </Text>
          <Space>
            <Button onClick={handleCancel}>取消</Button>
            <Button type="primary" disabled={disabled || !canSubmit} onClick={handleSubmit}>
              提交
            </Button>
          </Space>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size={12}>
        {question ? <Paragraph style={{ marginBottom: 0, fontSize: 13, fontWeight: 500 }}>{question}</Paragraph> : null}
        {hint ? <Text type="secondary" style={{ fontSize: 12 }}>{hint}</Text> : null}

        {options.length > 0 ? (
          <>
            <Divider style={{ margin: '4px 0' }} />
            <div style={{ maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {multiSelect ? (
                <Checkbox.Group
                  style={{ width: '100%' }}
                  value={selectedValues}
                  onChange={(values) => setSelectedValues(values.map((item) => String(item)))}
                >
                  {options.map((option: any, index: number) => renderOption(option, index))}
                </Checkbox.Group>
              ) : (
                <Radio.Group
                  style={{ width: '100%' }}
                  value={selectedValues[0] || ''}
                  onChange={(e) => setSelectedValues([String(e.target.value)])}
                >
                  {options.map((option: any, index: number) => renderOption(option, index))}
                </Radio.Group>
              )}
            </div>
          </>
        ) : (
          <Empty description="暂无候选，请手动输入" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}

        {manualAllowed ? (
          <>
            <Divider style={{ margin: '4px 0' }} />
            <Input.TextArea
              rows={2}
              value={manualText}
              disabled={disabled}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="可手动补充说明（选填）"
            />
          </>
        ) : null}
      </Space>
    </Modal>
  );
};

export default ClarificationCard;
