/**
 * CRA dev server 自定义代理（取代 package.json 里的 "proxy" 字段）。
 *
 * 关键修复：SSE / stream 接口不能被默认 proxy 缓冲。
 *   - text/event-stream 路径下：buffer/cache 必须关掉
 *   - 关 X-Accel-Buffering（nginx 风格）+ 显式 selfHandleResponse=false
 *
 * 验证方式：直连 8000  ↔  走 3000 proxy 两边的 first-event 时间应一致（毫秒级）。
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND = process.env.REACT_APP_API_PROXY_TARGET || 'http://127.0.0.1:28000';

module.exports = function (app) {
  // SSE / 流式路径：单独设置，关闭一切 buffering
  app.use(
    ['/api/v1/graph-query/map/stream', '/api/data-intelligence/chat/freeplan/stream'],
    createProxyMiddleware({
      target: BACKEND,
      changeOrigin: true,
      ws: false,
      // 重要：流式必须保留 chunked 传输；不要让 proxy 改写 content-encoding 或合并 body
      selfHandleResponse: false,
      // SSE 连接需要长超时（复杂查询可达 120s+）
      proxyTimeout: 0,
      timeout: 0,
      // 显式禁用 socket buffering
      onProxyReq(proxyReq) {
        // 防止 nginx / 中间层缓冲
        proxyReq.setHeader('X-Accel-Buffering', 'no');
        proxyReq.setHeader('Cache-Control', 'no-cache');
      },
      onProxyRes(proxyRes, req, res) {
        // 给浏览器一个明确的"别 buffer 我"的信号
        proxyRes.headers['X-Accel-Buffering'] = 'no';
        proxyRes.headers['Cache-Control'] = 'no-cache, no-transform';
        // 显式去掉可能触发 buffering 的 header
        delete proxyRes.headers['content-length'];
        delete proxyRes.headers['content-encoding'];
      },
    })
  );

  // 其它所有 /api/* 路径走默认 proxy
  app.use(
    ['/api'],
    createProxyMiddleware({
      target: BACKEND,
      changeOrigin: true,
      ws: false,
    })
  );
};
