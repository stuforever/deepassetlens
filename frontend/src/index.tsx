import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
import App from './App';
import AuthGate from './auth/AuthGate';
import AppErrorBoundary from './components/AppErrorBoundary';
import { initResizeObserverLoopGuard } from './utils/suppressResizeObserverLoop';

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
