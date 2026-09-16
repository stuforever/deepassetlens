/**
 * 组内私有：i18n t() 中文直出工具（批10 F3 移植约定 5）。
 * 原仓组件通过 react-i18next 的 t(key, opts) 取 web/locales/zh/app.json 译文；
 * tupu 无 i18next，改为查表直出：原译文优先，查无的 key 登记语义中文直出。
 * 插值 {{name}} 语义与 i18next 一致。所有组件内 t(...) 调用点逐字保留。
 */
const ZH: Record<string, string> = {
  // ── 原译文（web/locales/zh/app.json 查得）──
  Memory: "记忆",
  Refresh: "刷新",
  "Memory settings": "记忆设置",
  "L1 · Workspace mirror": "L1 · 工作区镜像",
  "L2 · Per-surface summaries": "L2 · 各模块摘要",
  "L3 · Cross-surface knowledge": "L3 · 跨模块知识",
  Live: "实时",
  Curated: "整理后",
  Synthesis: "综合",
  New: "新建",
  "Memory graph": "记忆图谱",
  "entities tracked": "条 workspace 实体",
  "facts across {{n}} surfaces": "条事实，共 {{n}} 个 surface",
  "propositions across {{n}} slots": "条命题，共 {{n}} 个 slot",
  "Snapshot of your live workspace across {{n}} surfaces. Refresh to record changes.":
    "对你 {{n}} 个 surface 工作区的快照。点击 Refresh 记录变化。",
  "Surface-specific facts extracted by the consolidator. Run Update / Audit / Dedup per doc.":
    "由 consolidator 抽取的、每个 surface 的事实。每个文档支持 更新 / 检查 / 去重。",
  "Cross-surface synthesis: profile, recent timeline, knowledge scope. Hedged claims with L2 evidence.":
    "跨 surface 综合：用户画像、近期时间线、知识 scope。每条判断都有 L2 证据。",
  "See all three layers at once — L3 synthesis at the centre, L2 facts in the middle, L1 traces on the outside. Hover any node for a preview.":
    "一次查看全部三层 —— 中心为 L3 综合，中圈为 L2 事实，外圈为 L1 原始事件。悬停任意节点可预览。",
  "Everything DeepTutor remembers about you, organised across three layers. Click into any layer to inspect or curate it.":
    "DeepTutor 关于你的全部记忆，分为三层组织。点击任何一层进入查看或整理。",
  Chat: "聊天",
  Notebook: "笔记本",
  Quiz: "测验",
  "Knowledge base": "知识库",
  Book: "书籍",
  Partner: "伙伴",
  "Co-writer": "Co-writer",
  "Recent summary": "近期总结",
  "User profile": "用户画像",
  "Knowledge scope": "知识 Scope",
  Saved: "已保存",
  "Save failed": "保存失败",
  "Edit raw": "编辑原文",
  Cancel: "取消",
  Save: "保存",
  Edit: "编辑",
  Update: "更新",
  Rendered: "渲染视图",
  "Line numbers": "带行号",
  "Empty. Click Update to extract facts from your traces.":
    "空。点击 更新 从原始 trace 中抽取事实。",
  "LLM workspace": "LLM 工作区",
  "Undo last memory edit": "撤销上一次记忆编辑",
  "Clear trace": "清空轨迹",
  "Update memory": "更新记忆",
  "Audit memory": "检查记忆",
  Dedup: "去重",
  "Loading models": "模型加载中",
  "Models unavailable": "模型不可用",
  "Default model": "默认模型",
  default: "默认",
  Run: "运行",
  "Working…": "处理中…",
  "System prompt": "System prompt",
  "User prompt": "User prompt",
  "Streaming…": "流式传输中…",
  "Run started": "运行已启动",
  "Traces loaded": "轨迹已加载",
  Progress: "进度",
  "Facts extracted": "已抽取的事实",
  "Ref dropped": "Ref 已丢弃",
  "Edit applied": "编辑已应用",
  "Edit rejected": "编辑已拒绝",
  "Markdown updated": "Markdown 已更新",
  "Undo applied": "撤销已应用",
  Done: "完成",
  "Run ended": "运行已结束",
  Error: "错误",
  "Your v1 memory was archived": "你的 v1 记忆已归档",
  Dismiss: "关闭",
  "L1 · Workspace": "L1 · Workspace",
  "L2 · Per-surface": "L2 · 各模块摘要",
  "L3 · Cross-surface": "L3 · 跨模块知识",
  Snapshot: "快照",
  Changes: "变更",
  Queries: "查询",
  "Clear focus": "取消高亮",
  "Nothing in workspace yet.": "Workspace 里暂时没有内容。",
  new: "新增",
  modified: "已修改",
  removed: "已删除",
  "Click Refresh to commit": "点击 Refresh 提交",
  "not built": "未构建",
  "Pick a document to view or update": "选择一个文档以查看或更新",
  "Update progress": "更新进度",
  "Refreshed: {{n}} changes": "已刷新：{{n}} 项变更",
  "Refreshed: no changes": "已刷新：无变更",
  "L3 · synthesis": "L3 · 综合",
  "L2 · curated": "L2 · 已归纳",
  "L1 · raw trace": "L1 · 原始事件",
  Profile: "配置文件",
  Recent: "近期",
  Scope: "范围",
  facts: "条事实",
  traces: "条事件",
  synthesis: "综合",
  "Composing memory graph…": "正在构建记忆图谱…",
  "Zoom in": "放大",
  "Zoom out": "缩小",
  Fit: "适配",
  "L3 synthesis at the centre, L2 facts in the middle ring, L1 traces on the outside.":
    "中心为 L3 综合，中圈为 L2 事实，外圈为 L1 原始事件。",
  "Hover a node to preview the memory. Click to lock the highlight and trace its references inward (L1 → L2 → L3) or outward.":
    "悬停节点可预览记忆。点击可锁定高亮，并追踪其向内（L1 → L2 → L3）或向外的引用关系。",
  "Click to lock · open in workbench": "点击锁定 · 在工作台中打开",
  "Per-surface": "各模块",
  "Raw traces": "原始事件",
  "stream failed": "流传输失败",
  "start failed: {{status}}": "启动失败：{{status}}",
  "start failed": "启动失败",
  "undo failed: {{status}}": "撤销失败：{{status}}",
  "undo failed": "撤销失败",
  "Reset will delete the current memory file AND its seen-id state. The next Update will re-ingest every L1 entity from scratch. Continue?":
    "重置将删除当前记忆文件以及 seen-id 状态。下次「更新」会从零重新摄取所有 L1 实体。是否继续？",
  "Reset failed: {{msg}}": "重置失败：{{msg}}",
  "unknown error": "未知错误",
  "reset failed: {{status}}": "重置失败：{{status}}",
  "Pick a mode and click Run. The LLM trace — system prompt, user prompt, response — appears here, turn by turn.":
    "选择一个模式并点击「运行」。LLM 轨迹（system prompt、user prompt、response）将按轮次显示在此处。",
  "Stored at memory/backup/{{name}}. v2 starts fresh — interact with DeepTutor and click Update on each doc to build memory.":
    "已存储到 memory/backup/{{name}}。v2 从零开始 — 与 DeepTutor 交互，并对每个文档点击「更新」以构建记忆。",
  "Live snapshot of your workspace — one entry per real artifact.":
    "Workspace 的实时快照——每条对应一个真实产物。",
  "Per-surface summaries consolidated from L1 content.":
    "基于 L1 内容归纳出的各模块摘要。",
  "Cross-surface knowledge consolidated from L2.": "由 L2 跨模块归纳的整体认知。",
  "No changes recorded yet. Run Refresh to capture the baseline.":
    "尚无变更记录。点击 Refresh 建立基线。",
  "No RAG queries recorded yet.": "尚未记录任何 RAG 查询。",
  "Open in {{label}}": "在 {{label}} 中打开",
  "Pending — not yet committed to changes log": "待提交 — 尚未写入变更日志",
  "Pending — {{n}} change(s) since last refresh":
    "待提交 — 上次刷新后有 {{n}} 个变化",
  "{{n}} entities": "{{n}} 条实体",
  "{{n}} pending": "{{n}} 个待提交",
  "last refresh {{ts}}": "上次刷新 {{ts}}",
  "Re-scan workspace and record any changes": "重新扫描 workspace 并记录变更",
  "Workspace changed since last refresh. Click Refresh to commit these to the changes log.":
    "上次刷新之后 workspace 有变化，点击 Refresh 把这些变化提交到变更日志。",
  "Preferences is written by the chat assistant, not consolidated.":
    "偏好由聊天助手写入，不经过 consolidate。",
  "Preferences are written when you explicitly tell the chat assistant your preferences (style, language, format).":
    "当你向聊天助手明确告知偏好（风格、语言、格式）时，偏好才会被写入。",
  "Empty. Click Update to consolidate from the current snapshot.":
    "暂无内容。点 Update 基于当前快照生成摘要。",
  // ── 原译文查无，语义直出（登记）──
  L1: "L1",
  L2: "L2",
  L3: "L3",
  Reset: "重置",
  "Reset memory (delete md + seen-id state)": "重置记忆（删除 md 与 seen-id 状态）",
  Iter: "次数",
  Budget: "预算",
  Cancelled: "已取消",
  Chunked: "分块",
  "Resolving entry…": "正在解析条目…",
  "Back to memory": "返回记忆",
  "Entry {{id}} not found in any L2 doc — it may have been deleted.":
    "条目 {{id}} 在任何 L2 文档中都未找到——它可能已被删除。",
  "Resolver failed ({{code}})": "解析失败（{{code}}）",
  "Resolver failed": "解析失败",
  "Missing ?id= in URL": "URL 中缺少 ?id=",
  "L1 mirrors your workspace, L2 summarises per-surface content, L3 is cross-surface knowledge.":
    "L1 镜像你的工作区，L2 汇总各模块内容，L3 是跨模块知识。",
  "Failed to load overview": "加载总览失败",
  "Failed to load document": "加载文档失败",
  "Update failed": "更新失败",
  "Failed to load snapshot": "加载快照失败",
  "Failed to load changes": "加载变更失败",
  "Failed to load queries": "加载查询失败",
  "Refresh failed": "刷新失败",
  题库: "题库",
};

/** i18next 兼容直出：查表，未命中直出 key；支持 {{name}} 插值。 */
export function t(key: string, opts?: Record<string, unknown>): string {
  const zh = Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
  if (!opts) return zh;
  return zh.replace(/\{\{(\w+)\}\}/g, (_m, k: string) =>
    opts[k] !== undefined && opts[k] !== null ? String(opts[k]) : `{{${k}}}`,
  );
}
