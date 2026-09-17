# -*- coding: utf-8 -*-
"""批2 探针3：WS 握手诊断——/api/v1/ws 经 23000 代理能否连上。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:23000/", timeout=30000)
    pg.wait_for_timeout(2000)
    res = pg.evaluate(
        """() => new Promise((resolve) => {
          const out = { opened: false, errored: null, closed: null };
          let ws;
          try {
            ws = new WebSocket('ws://localhost:23000/api/v1/ws');
          } catch (e) { out.errored = String(e); resolve(out); return; }
          const done = () => { try { ws.close(); } catch (e) {} resolve(out); };
          ws.onopen = () => { out.opened = true; done(); };
          ws.onerror = (e) => { out.errored = out.errored || 'error-event'; };
          ws.onclose = (e) => { out.closed = 'code=' + e.code; if (!out.opened) done(); };
          setTimeout(() => { if (!out.opened && !out.closed) done(); }, 5000);
        })"""
    )
    print("WS /api/v1/ws:", res)
    res2 = pg.evaluate(
        """() => new Promise((resolve) => {
          const out = { opened: false, errored: null, closed: null };
          let ws;
          try {
            ws = new WebSocket('ws://localhost:23000/ws');
          } catch (e) { out.errored = String(e); resolve(out); return; }
          const done = () => { try { ws.close(); } catch (e) {} resolve(out); };
          ws.onopen = () => { out.opened = true; done(); };
          ws.onerror = (e) => { out.errored = out.errored || 'error-event'; };
          ws.onclose = (e) => { out.closed = 'code=' + e.code; if (!out.opened) done(); };
          setTimeout(() => { if (!out.opened && !out.closed) done(); }, 5000);
        })"""
    )
    print("WS /ws (HMR):", res2)
    b.close()
