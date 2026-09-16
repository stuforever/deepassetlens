/**
 * 等价替换 stub：DeepTutor 原仓 web/context/AppShellContext.tsx（280 行）在本仓
 * 不存在。按"最小等价"提供同名 Context + useAppShell()，字段集与原
 * AppShellContextValue 完全一致（BookChatPanel/BookCreator 实际仅解构
 * `language`，随 StartTurnMessage.language 传给后端；其余字段一并给出以防
 * 同批其它复刻组件解构），取安全默认值：函数字段 no-op、对象/字符串取字面量
 * 默认、开关 false。tupu 为中文产品，language 默认 'zh'（原仓 SSR 期默认 'en'
 * 后从 localStorage 水合）。无 Provider 时直接返回默认值，不抛错。
 */
import { createContext, useContext } from "react";
import type { ReactNode } from "react";

export type AppTheme = "light" | "dark" | "system";
export type AppLanguage = "en" | "zh";

export interface AppShellContextValue {
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
  language: AppLanguage;
  setLanguage: (language: AppLanguage) => void;
  activeSessionId: string | null;
  setActiveSessionId: (sessionId: string | null) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  codeBlockTheme: string;
  setCodeBlockTheme: (theme: string) => void;
  codeBlockShowLineNumbers: boolean;
  setCodeBlockShowLineNumbers: (show: boolean) => void;
  codeBlockWrapLongLines: boolean;
  setCodeBlockWrapLongLines: (wrap: boolean) => void;
}

const noop = () => {};

const defaultAppShellValue: AppShellContextValue = {
  theme: "light",
  setTheme: noop,
  language: "zh",
  setLanguage: noop,
  activeSessionId: null,
  setActiveSessionId: noop,
  sidebarCollapsed: false,
  setSidebarCollapsed: noop,
  codeBlockTheme: "github",
  setCodeBlockTheme: noop,
  codeBlockShowLineNumbers: false,
  setCodeBlockShowLineNumbers: noop,
  codeBlockWrapLongLines: false,
  setCodeBlockWrapLongLines: noop,
};

export const AppShellContext =
  createContext<AppShellContextValue>(defaultAppShellValue);

/** 兼容原 Provider 用法：stub 无状态，直接透传默认值。 */
export function AppShellProvider({ children }: { children: ReactNode }) {
  return (
    <AppShellContext.Provider value={defaultAppShellValue}>
      {children}
    </AppShellContext.Provider>
  );
}

export function useAppShell(): AppShellContextValue {
  return useContext(AppShellContext);
}
