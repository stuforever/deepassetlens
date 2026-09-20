/**
 * CRA dev server 自定义代理（取代 package.json 里的 "proxy" 字段）。
 *
 * 关键修复：SSE / stream 接口不能被默认 proxy 缓冲。
 *   - text/event-stream 路径下：buffer/cache 必须关掉
 *   - 关 X-Accel-Buffering（nginx 风格）+ 显式 selfHandleResponse=false
 *
 * 验证方式：直连 28000  ↔  走 23000 proxy 两边的 first-event 时间应一致（毫秒级）。
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
        // 三轨M6 顺手修(:33)：请求方向声明不接收压缩——上游若 gzip，浏览器收到的
        // 字节流经 delete content-encoding 后会当明文解析（SSE 乱码/断流根因）。
        proxyReq.setHeader('Accept-Encoding', 'identity');
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

  // IA批2：/api 代理启用 ws:true——vendor 聊天走 /api/v1/ws WebSocket（unified-ws.ts），
  // 原仓 web/proxy.ts 转发 WS，dev 代理此前缺位致 h5 发送"WebSocket failed to connect"。
  // 实测：scoped '/api/v1/ws' 挂载 HPM upgrade 不生效（握手悬挂），'/api' 全局 ws:true 可用。
  app.use(
    ['/api'],
    createProxyMiddleware({
      target: BACKEND,
      changeOrigin: true,
      ws: true,
    })
  );
};
