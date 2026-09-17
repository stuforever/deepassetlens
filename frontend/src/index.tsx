import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
// 引擎批2：DT 桌面窗口主题/动画层 + i18next（keySeparator=false，zh 资源即键直查）
import './dt-globals.css';
import { initI18n } from './i18n/init';
import App from './App';
import AuthGate from './auth/AuthGate';
import AppErrorBoundary from './components/AppErrorBoundary';
import { initResizeObserverLoopGuard } from './utils/suppressResizeObserverLoop';

// i18next 模块加载即初始化（DT I18nProvider 同语义：init 事件不得落在其他组件渲染期）
initI18n();

// ResizeObserver loop 是 antd/rc-table 等第三方库的良性告警（无实际影响），
// 在 render 前注册：①根因修复——回调延迟到下一帧，浏览器不再报循环；
// ②兜底——捕获阶段吞掉该特定错误消息，避免污染控制台/触发 webpack 浮层。
initResizeObserverLoopGuard();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <AppErrorBoundary>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthGate>
          <App />
        </AuthGate>
      </BrowserRouter>
    </AppErrorBoundary>
  </React.StrictMode>
);
