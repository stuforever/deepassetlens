/**
 * CommandPalette（v3 #8 / Task 4）：⌘K/Ctrl+K 命令面板——全部页面 + 三专家动作 + 快捷动作。
 * 键盘 ↑↓ 导航 + Enter 执行 + Esc 关闭；顶栏搜索框点击唤起同一面板。
 * 批③ 审查Minor②：同指 path 去重留最优 label（页面注册项先于专家/快捷动作注册，first-wins 胜出）。
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Input, Modal } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { menuKeyToPath, MENU_LABELS, REDIRECT_ONLY_MENU_KEYS } from '../../config/navigation';
import { EXPERT_PAGES } from '../../config/expertPages';

export interface CommandItem {
  key: string;
  label: string;
  hint?: string;
  run: () => void;
}

export function buildCommandItems(navigate: (path: string) => void): CommandItem[] {
  const items: CommandItem[] = [];
  // UX批①：专家对话页可检索性——页签项 label（数据探索对话/私塾先生对话）不含专家俗称，
  // ⌘K 搜「问数/私塾」零结果=用户反馈①②口子；hint 进过滤面（label OR hint 匹配），
  // 点击即单跳 /e/{slug}/chat（页签项本身即真实路径——无需专家重复条目，按 path 去重使其为死代码）
  const EXPERT_HINTS: Record<string, string> = {
    'e:wenshu:chat': '问数',
    'e:sishu:chat': '私塾',
    'e:tutor-h5:chat': 'h5 展台',
  };
  // 全部页面（routes 静态注册 + 专家页注册表——label+path 模糊）
  const seen = new Set<string>();
  const push = (key: string, label: string, path: string, hint?: string) => {
    if (seen.has(path)) return; // 批③ 审查Minor②：仅按 path 去重（first-wins——页面规范 label 胜出，同指专家/快捷动作被吸收）
    seen.add(path);
    items.push({ key, label, hint, run: () => navigate(path) });
  };
  for (const [menuKey, path] of Object.entries(menuKeyToPath)) {
    if (menuKey.startsWith('settings:')) continue; // 子页经设置面板/设置中心内部导航，面板只留分区入口
    if (menuKey === 'home') continue; // /home 重定向 /（避免面板双首页项）
    if (REDIRECT_ONLY_MENU_KEYS.has(menuKey)) continue; // 批③ 审查Minor①：4合1 退役页不再露出
    push(`page-${menuKey}`, MENU_LABELS[menuKey] || menuKey, path, EXPERT_HINTS[menuKey]);
  }
  // 快捷动作
  push('action-newchat', '新建对话', '/', '动作');
  push('action-settings', '打开设置', '/settings', '动作');
  push('action-h5publish', 'H5 发布管理', '/h5-publish', '动作');
  return items;
}

const CommandPalette: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const all = useMemo(() => buildCommandItems(navigate), [navigate]);
  const items = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return all.slice(0, 12);
    return all
      .filter((it) => it.label.toLowerCase().includes(s) || (it.hint || '').toLowerCase().includes(s))
      .slice(0, 12);
  }, [all, q]);

  useEffect(() => { setIdx(0); }, [q, open]);
  useEffect(() => {
    if (open) {
      setQ('');
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  const exec = (it?: CommandItem) => {
    if (!it) return;
    onClose();
    it.run();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(i + 1, items.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); exec(items[idx]); }
    else if (e.key === 'Escape') { onClose(); }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={560}
      styles={{ body: { padding: 0 } }}
      title={null}
      closable={false}
    >
      <div data-testid="cmdk" onKeyDown={onKeyDown}>
        <Input
          ref={inputRef as never}
          size="large"
          prefix={<SearchOutlined style={{ color: 'var(--text-tertiary, #bbb)' }} />}
          placeholder="搜索页面、专家、动作…（↑↓ 选择，回车执行）"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          variant="borderless"
          data-testid="cmdk-input"
        />
        <div style={{ maxHeight: 380, overflowY: 'auto', borderTop: '1px solid var(--border-subtle, #eee)' }}>
          {items.length === 0 && (
            <div style={{ padding: 16, fontSize: 13, color: 'var(--text-tertiary, #999)' }}>无匹配结果</div>
          )}
          {items.map((it, i) => (
            <div
              key={it.key}
              role="button"
              tabIndex={0}
              data-testid={`cmdk-item-${i}`}
              onMouseEnter={() => setIdx(i)}
              onClick={() => exec(it)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '9px 16px', cursor: 'pointer',
                fontSize: 13.5, background: i === idx ? 'var(--primary-50, #eff6ff)' : 'transparent',
                color: i === idx ? 'var(--brand, #2563EB)' : 'inherit',
              }}
            >
              <span style={{ flex: 1 }}>{it.label}</span>
              {it.hint && (
                <span style={{ fontSize: 11, color: 'var(--text-tertiary, #aaa)', border: '1px solid var(--border-subtle, #eee)', borderRadius: 6, padding: '1px 6px' }}>
                  {it.hint}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
};

export default CommandPalette;
