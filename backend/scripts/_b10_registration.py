# -*- coding: utf-8 -*-
"""批10 F3 映射登记：原仓 (admin)/(auth)/(utility) 组 → tupu 承接位。逐页事实清点。"""
import json
import re
from pathlib import Path

ORIG = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web\app")
OUT = Path(__file__).resolve().parent / "dt_baseline" / "batch10_映射登记.json"

def lines(p):
    try:
        return len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        return -1

def apis(p):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return sorted(set(re.findall(r'/api/v1/[a-z0-9\-/{}\[\]_$]+', t)))

def shells(p):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return sorted(set(re.findall(r'from "@/components/([^"]+)"', t)))

REG = []
def reg(page, n_lines, target, batch, status, note=""):
    REG.append({
        "page": page, "orig_lines": n_lines, "tupu_target": target,
        "batch": batch, "status": status, "note": note,
        "api_surface": apis(ORIG / page) if status != "不复刻" else [],
        "component_imports": shells(ORIG / page),
    })

# ---- (admin) ----
reg("(admin)/admin/users/page.tsx", 599, "ExpertGrants（批17 尾步 users 并入）", "批17", "登记衔接",
    "用户管理语义（列表/角色/启停）并入赋权页；本批登记映射与端点面，实作随批17")
# ---- (auth) ----
reg("(auth)/login/page.tsx", 155, "⑥-2a 登录（auth=1 实测项已收口）", "批19", "登记承接",
    "登录跳转/登出/401 拦截已在 19.1 实现（OIDC /api/v1/auth/config 驱动）")
reg("(auth)/register/page.tsx", 173, "⑥-2a（Authentik 注册流）", "批19", "登记承接",
    "tupu 登录走 Authentik 9100 OIDC；原自建 register 表单不复刻，注册由 SSO 承担")
# ---- (utility) 批10 实作 ----
reg("(utility)/memory/page.tsx", 10, "MemoryAdmin「Hub 总览」tab", "批10", "并入",
    "memory 六件 1:1 进 pages/memory/，MemoryAdmin Tabs 单套不双轨")
reg("(utility)/memory/l1/page.tsx", 58, "MemoryAdmin「L1 工作台」tab", "批10", "并入",
    "deep-link ?surface=&ref= → tab 内 state")
reg("(utility)/memory/l2/page.tsx", 5, "MemoryAdmin「L2 工作台」tab", "批10", "并入", "MemoryWorkbench layer=L2")
reg("(utility)/memory/l3/page.tsx", 5, "MemoryAdmin「L3 工作台」tab", "批10", "并入", "MemoryWorkbench layer=L3")
reg("(utility)/memory/graph/page.tsx", 5, "MemoryAdmin「记忆图谱」tab", "批10", "并入", "")
reg("(utility)/memory/resolve/page.tsx", 95, "MemoryAdmin「解析定位」tab", "批10", "并入",
    "resolve 302 语义 → 内嵌输入 id→resolve_entry→切 tab 定位 focus")
reg("(utility)/memory/l2/[surface]/page.tsx", 35, "同上（deep-link 参数面）", "批10", "并入", "")
reg("(utility)/memory/l3/[slot]/page.tsx", 25, "同上（deep-link 参数面）", "批10", "并入", "")
# ---- (utility) 登记映射 ----
reg("(utility)/knowledge/page.tsx", 17, "④知识库管理（批2 契约适配层）", "批2/批11", "登记",
    "knowledge 域形状由 dt_knowledge_adapter 1:1 提供（tutor_routers 已挂载）")
reg("(utility)/agents/page.tsx", 10, "③连接实例（平台 agent 域）", "批10", "登记映射",
    "agents 六家（claude-code/codex/gemini/kimi/mimo/opencode settings 壳）=③连接实例语义；tupu 平台连接管理已有等价件")
for a in ["claude-code", "codex", "gemini", "kimi", "mimo", "opencode"]:
    reg(f"(utility)/settings/agents/{a}/page.tsx", 5, "③连接实例", "批10", "登记映射", "agents 六家壳")
reg("(utility)/profile/page.tsx", 387, "用户态（平台个人面板）", "批10", "登记",
    "profile 语义（个人资料/偏好）由平台用户态承担；教学域画像=learner-profile 域（已挂载）")
reg("(utility)/settings/appearance/page.tsx", 211, "用户态（主题/外观）", "批10", "登记",
    "主题语义 tupu 走 antd 主题令牌；PUT /theme 端点已随 settings 路由挂载")
reg("(utility)/settings/chat/page.tsx", 4, "用户态（chat 偏好）", "批10", "登记",
    "PUT /chat-response-timeout 等端点已挂载")
reg("(utility)/settings/attachments/page.tsx", 251, "平台补最小件（chat-attachments 设置）", "批10", "差距补件",
    "GET/PUT /api/v1/settings/chat-attachments 已挂载（真缺口闭合）；设置 UI 以平台附件能力（批8 file/doc-attachments + attachment-limits）为基，超限语义一致")
reg("(utility)/notebook/page.tsx", 642, "平台 notebook 语义（单套）", "批10", "登记",
    "notebook 域 API 已挂载（/api/v1/notebook 8 端点）；桌面 notebook 页=工作台笔记面，h5 笔记 tab（批9）+平台记录面同源 API，单套不双轨")
reg("(workspace)/playground/page.tsx", 1921, "不复刻（等价物已有）", "批10", "不复刻",
    "playground=提示词试验场；tupu 平台 LLM 配置+引擎工作台已承担等价能力，总账 10.2 明示不复刻")
# ---- 不复刻 ----
reg("(utility)/settings/capabilities/page.tsx", 564, "capabilities 端点已挂载；UI=平台能力管理", "批10", "登记",
    "GET/PUT /api/v1/capabilities/settings 已挂载；tupu 能力管理页已有等价面")

# settings 其余组页（curriculum 已批8；document-parsing/network/tools/mcp/memory-settings/status/tts 等壳）
for rel, ln in [
    ("(utility)/settings/curriculum/page.tsx", 5),
    ("(utility)/settings/curriculum/textbooks/page.tsx", 246),
    ("(utility)/settings/curriculum/chapters/page.tsx", 259),
    ("(utility)/settings/curriculum/knowledge-points/page.tsx", 857),
]:
    reg(rel, ln, "SettingsAdmin（批8 课本/章节/知识点管理 tab）", "批8", "已承接", "")

report = {
    "batch": "批10 F3 平台组承接与合并",
    "backend_mounts": {
        "memory": "/api/v1/memory 28 端点（活探 overview 200）",
        "settings": "/api/v1/settings 45 端点（活探 llm-options/chat-attachments 200）",
        "capabilities_settings": "/api/v1/capabilities/settings（活探 200）",
        "mcp_settings": "/api/v1/settings/mcp（活探 200）",
        "fidelity": "四件 vendor 文件 sha256 与原仓逐一致零改码",
    },
    "registrations": REG,
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"登记 {len(REG)} 项 → {OUT}")
for r in REG:
    print(f"  {r['page']}: {r['orig_lines']}行 → {r['tupu_target']} [{r['status']}]")
