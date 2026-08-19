import React from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  message?: string;
}

/**
 * 全局错误边界：兜底路由懒加载 chunk 失败 / 渲染异常，
 * 避免白屏，并给出可恢复提示（刷新重试）。
 */
class AppErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(err: unknown): State {
    return { hasError: true, message: err instanceof Error ? err.message : String(err) };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    // 日志/监控接入点
    console.error('[AppErrorBoundary]', error, info);
  }

  handleReload = () => {
    this.setState({ hasError: false });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 600 }}>页面加载失败</div>
          <div style={{ color: '#888', maxWidth: 480, textAlign: 'center' }}>
            {this.state.message || '未知错误，请刷新重试'}
          </div>
          <button onClick={this.handleReload} style={{ padding: '6px 16px', cursor: 'pointer' }}>
            刷新重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default AppErrorBoundary;
