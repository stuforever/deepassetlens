/**
 * PageIndex 凭证设置弹窗（复刻 DeepTutor web/components/knowledge/PageIndexSettingsModal.tsx → tupu antd 5）。
 *
 * 源 @/components/common/Modal（width=md=500px、saving 时禁止关闭）→ antd Modal 等价映射：
 *   isOpen→open、closeOnBackdrop→maskClosable、closeOnEscape→keyboard、
 *   onClose 守卫（saving 时 no-op）→onCancel；titleIcon=KeyRound→KeyOutlined。
 * 区块：说明段落 → loading（Spin）→ API 密钥（password，已配置时「移除已存密钥」）→
 *   API 基础地址 → 错误框（红）；Footer：左「获取 API 密钥」外链 + 右「取消/保存」。
 * 空密钥提交保留已存键；填值则替换；成功后 onSaved + onClose。
 * 文案：t('English') → 中文（zh/app.json 收录键）。
 */
import React, { useEffect, useState } from 'react';
import { Alert, Button, Input, Modal, Spin } from 'antd';
import { ExportOutlined, KeyOutlined } from '@ant-design/icons';
import {
  getPageIndexConfig,
  updatePageIndexConfig,
  type PageIndexConfig,
} from './knowledge-api';
import { colors } from '../../theme/tokens';

const DEFAULT_BASE_URL = 'https://api.pageindex.ai';

interface PageIndexSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Called after a successful save so callers can refresh provider state. */
  onSaved?: () => void;
}

export default function PageIndexSettingsModal({
  isOpen,
  onClose,
  onSaved,
}: PageIndexSettingsModalProps) {
  const [config, setConfig] = useState<PageIndexConfig | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setApiKey('');
    getPageIndexConfig({ force: true })
      .then((cfg) => {
        if (cancelled) return;
        setConfig(cfg);
        setBaseUrl(cfg.api_base_url || '');
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  const persist = async (payload: {
    api_key?: string;
    api_base_url?: string;
  }) => {
    setSaving(true);
    setError(null);
    try {
      const next = await updatePageIndexConfig(payload);
      setConfig(next);
      setApiKey('');
      onSaved?.();
      return next;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    // Blank key keeps the stored one; a typed value replaces it.
    const payload: { api_key?: string; api_base_url?: string } = {
      api_base_url: baseUrl.trim() || undefined,
    };
    if (apiKey.trim()) payload.api_key = apiKey.trim();
    const next = await persist(payload);
    if (next) onClose();
  };

  const keySet = config?.api_key_set ?? false;
  const fieldLabelStyle: React.CSSProperties = {
    marginBottom: 4,
    display: 'block',
    fontSize: 11,
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: colors.textSecondary,
  };

  return (
    <Modal
      open={isOpen}
      width={500}
      title={
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
          <KeyOutlined style={{ fontSize: 16 }} />
          PageIndex 设置
        </span>
      }
      onCancel={saving ? () => undefined : onClose}
      maskClosable={!saving}
      keyboard={!saving}
      footer={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <a
            href="https://dash.pageindex.ai/api-keys"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              fontSize: '11.5px',
              color: colors.textSecondary,
            }}
          >
            获取 API 密钥
            <ExportOutlined style={{ fontSize: 12 }} />
          </a>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button
              type="text"
              onClick={onClose}
              disabled={saving}
              style={{ fontSize: '12.5px', fontWeight: 500, color: colors.textSecondary, height: 'auto', padding: '6px 12px' }}
            >
              取消
            </Button>
            <Button
              type="primary"
              onClick={() => void handleSave()}
              disabled={saving || loading}
              loading={saving}
              style={{ fontSize: '12.5px', fontWeight: 500, height: 'auto', padding: '6px 14px' }}
            >
              保存
            </Button>
          </div>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <p style={{ margin: 0, fontSize: '12.5px', lineHeight: 1.7, color: colors.textSecondary }}>
          PageIndex 是托管的无向量检索引擎。PageIndex 知识库中的文档会上传到 PageIndex 服务器进行处理。同一个密钥由你所有的 PageIndex 知识库共用。
        </p>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 0' }}>
            <Spin size="small" />
          </div>
        ) : (
          <>
            <div>
              <label style={fieldLabelStyle}>API 密钥</label>
              <Input.Password
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                disabled={saving}
                visibilityToggle={false}
                placeholder={
                  keySet
                    ? '•••••••• （已配置，留空则保留）'
                    : '输入你的 PageIndex API 密钥'
                }
              />
              {keySet && (
                <Button
                  type="link"
                  danger
                  onClick={() => void persist({ api_key: '' })}
                  disabled={saving}
                  style={{ marginTop: 6, fontSize: 11, fontWeight: 500, height: 'auto', padding: 0 }}
                >
                  移除已存密钥
                </Button>
              )}
            </div>

            <div>
              <label style={fieldLabelStyle}>API 基础地址</label>
              <Input
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                disabled={saving}
                placeholder={DEFAULT_BASE_URL}
              />
            </div>
          </>
        )}

        {error && <Alert type="error" message={error} />}
      </div>
    </Modal>
  );
}
