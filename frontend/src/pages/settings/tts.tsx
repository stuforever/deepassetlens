/**
 * 批5 5.3：/settings/tts（源 (utility)/settings/tts/page.tsx 逐字移植）。
 * 差异登记：
 * 1. 源 "use client"/react-i18next 层省略——t('English') 直接取 locales/zh/app.json 译文；
 * 2. 源 useVoiceAutoplayPreference（web/hooks/useVoiceAutoplay）依赖源仓 api 层——tupu 清单外
 *    不落 hook 文件，本页内联等价实现（fetch 相对路径，setupProxy 统一转发 28000，不硬编码端口）；
 * 3. 源手写 switch 按钮（lucide 风格）→ antd Switch（lucide→antd 最近组件规约）；
 * 4. 共享组件 ServiceConfigEditor / SettingsPageHeader(shared) 为并行件（按名 import，暂红属预期）。
 */
import { useCallback, useEffect, useState } from 'react';
import { Switch } from 'antd';

import { ServiceConfigEditor } from '../../components/settings/ServiceConfigEditor';
import { SettingsPageHeader } from '../../components/settings/shared';
import { tokens } from '../../theme/tokens';

/**
 * 内联等价：源 web/hooks/useVoiceAutoplay.ts 的 useVoiceAutoplayPreference
 * （Settings 页 hook——读写持久化的全局默认值 ui.voice_autoplay）。
 */
function useVoiceAutoplayPreference() {
  const [value, setValueState] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let active = true;
    fetch('/api/v1/settings')
      .then((r) => (r.ok ? r.json() : null))
      .then((payload) => {
        if (!active) return;
        setValueState(Boolean(payload?.ui?.voice_autoplay));
        setLoading(false);
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const setValue = useCallback(async (next: boolean) => {
    setValueState(next);
    try {
      await fetch('/api/v1/settings/voice-autoplay', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_autoplay: next }),
      });
    } catch {
      // 忽略网络错误：本地状态先行（与源语义一致）
    }
  }, []);

  return { value, setValue, loading };
}

function AutoplayToggle() {
  const { value, setValue, loading } = useVoiceAutoplayPreference();
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 24,
        borderRadius: 12,
        border: `1px solid ${tokens.colors.border}`,
        background: tokens.colors.bgSubtle,
        padding: '16px 20px',
      }}
    >
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 13.5, fontWeight: 500, color: tokens.colors.textPrimary }}>
          自动朗读回复
        </div>
        <p style={{ margin: '4px 0 0', fontSize: 12, lineHeight: 1.6, color: tokens.colors.textSecondary }}>
          自动朗读每条助手回复。你也可以在每个对话中通过喇叭按钮单独开关。
        </p>
      </div>
      <Switch
        checked={value}
        disabled={loading}
        onChange={() => void setValue(!value)}
        aria-label="自动朗读回复"
        data-testid="tts-autoplay-toggle"
        style={{ marginTop: 2, flexShrink: 0 }}
      />
    </div>
  );
}

export default function TtsSettingsPage() {
  return (
    <div>
      <SettingsPageHeader
        title="语音合成"
        description="从聊天的喇叭按钮朗读助手回复。兼容任意 OpenAI 风格的音频接口——OpenAI、OpenRouter、Groq、SiliconFlow、Azure 或本地服务。"
      />

      <ServiceConfigEditor service="tts" />

      <section style={{ marginTop: 40 }}>
        <div style={{ marginBottom: 12 }}>
          <h2
            style={{
              margin: 0,
              fontSize: 15,
              fontWeight: 600,
              letterSpacing: '-0.01em',
              color: tokens.colors.textPrimary,
            }}
          >
            播放
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: 12.5, lineHeight: 1.6, color: tokens.colors.textSecondary }}>
            语音回复在聊天中的行为。
          </p>
        </div>
        <AutoplayToggle />
      </section>
    </div>
  );
}
