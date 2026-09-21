"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
# -*- coding: utf-8 -*-
from fastapi import Depends

# 原导入路径零改码（vendor 子树原结构）
from app.services.sishu_full.api.routers.auth import require_auth as _dt_require_auth  # noqa: E402
from app.services.sishu_full.api.routers import auth as auth_router  # noqa: E402
from app.services.sishu_full.api.routers import chat as chat_router  # noqa: E402

# 原仓 main.py `_auth = [Depends(require_auth)]` 的同位接线（指 vendor 内 auth 模块）：
# Header/Cookie 形签名对 WS 路由可解（原仓注释即为此设计）；AUTH_ENABLED=false 时放行
# 并安装桌面语义用户——与 dt_auth_shim 在 auth=0 下行为等价；auth=1 实测项归批18/20.2/20.3。
_auth = [Depends(_dt_require_auth)]

# 原导入路径零改码（vendor 子树原结构）
from app.services.sishu_full.api.routers import mother_question  # noqa: E402
from app.services.sishu_full.api.routers import knowledge as knowledge_router  # noqa: E402
# 引擎批6 6.5：question/quiz_judge 导入随卸挂删除（vendor 物理文件保留）
from app.services.sishu_full.api.routers import (  # noqa: E402
    learner_profile,
    mastery_path,
    self_learning,
)
from app.services.sishu_full.api.routers import (  # noqa: E402
    agent_config,
    attachments,
    co_writer,
    partners,
    personas,
    plugins_api,
    skills,
    space_cli_apps,
    space_mcp,
    subagents,
    system,
    # 引擎批6 6.3：unified_ws 导入随卸挂删除（router 不再挂载）
)
from app.services.sishu_full.api.routers import (  # noqa: E402
    book,
    capabilities_settings,
    dashboard,
    h5_links,
    imports,
    mcp_settings,
    memory,
    notebook,
    question_notebook,
    sessions,
    settings,
    voice,
    wechat_push,
)
from app.services.sishu_full.api.routers import tools as tools_router  # noqa: E402
from app.services.sishu_full.multi_user.router import router as multi_user_router  # noqa: E402
from app.services.sishu_full.api.routers.auth import require_admin as _dt_require_admin  # noqa: E402
from app.services.sishu_full.learning.curriculum import router as curriculum_router  # noqa: E402

# 原仓 main.py L551 `_admin = [Depends(require_admin)]`（partners 域——管理面路由族）
_admin = [Depends(_dt_require_admin)]

tutor_routers = [
    (mother_question.router, "/api/v1/mother-questions", ["mother-questions"], _auth),
    (curriculum_router, "/api/v1/curriculum", ["curriculum"], _auth),
    # ⑤R B1 3.2：knowledge 域原形状路由（契约适配层见 app/api/dt_knowledge_adapter.py——
    # 形状由本路由 1:1 提供；④挂接=注册表镜像+tutor 卡 knowledge_sources）
    (knowledge_router.router, "/api/v1/knowledge", ["knowledge"], _auth),
    # ⑤R B2：问答判题练习件——question(WS mimic/generate)+quiz_judge(WS judge)
    # 原挂载（原仓 main.py L442/L566）：question 带 _auth，quiz_judge 自带 ws_require_auth
    # 引擎批6 6.5：两族 WS 卸挂——前端消费 grep 实测零（question REST 无消费、
    # quiz_judge 消费方批4/6 切桥 lib/quiz-judge-bridge.ts）；vendor 物理文件保留。
    # ⑤R B3：学习闭环——原挂载（原仓 main.py L448/L458/L571）
    (learner_profile.router, "/api/v1/learning", ["learner-profile"], _auth),
    (mastery_path.router, "/api/v1/learning", ["mastery-path"], _auth),
    (self_learning.router, "/api/v1/self-learning", ["self-learning"], _auth),
    # ⑤R B4：配套件——原挂载（原仓 main.py L453/L455/L480/L482/L494/L578/L586/L537/L538）
    (notebook.router, "/api/v1/notebook", ["notebook"], _auth),
    (question_notebook.router, "/api/v1/question-notebook", ["question-notebook"], _auth),
    (book.router, "/api/v1/book", ["book"], _auth),
    (imports.router, "/api/v1/imports", ["imports"], _auth),
    (dashboard.router, "/api/v1/dashboard", ["dashboard"], _auth),
    (h5_links.router, "/api/v1/h5-links", ["h5-links"], _auth),
    (h5_links.settings_router, "/api/v1/h5-settings", ["h5-settings"], _auth),
    # 1.10 判定=全还原（前会话对账）：voice/wechat_push 原挂载（原 main.py L537/L538）
    (voice.router, "/api/v1/voice", ["voice"], _auth),
    (wechat_push.router, "/api/v1/wechat", ["wechat-push"], _auth),
    # ⑤R F2（批9）：sessions 原挂载（原 main.py L491）——h5/chat 会话列表/重命名/删除/
    # 分支选择/quiz-results 消费方（端点审计 _b9_endpoint_audit 活探 404→真缺口）
    (sessions.router, "/api/v1/sessions", ["sessions"], _auth),
    # ⑤R F3（批10）：memory 原挂载（原 main.py L483）——memory 分层视图并入
    # MemoryAdmin（单套不双轨）的端点面：overview/doc CRUD/runs/trace/snapshot/resolve
    (memory.router, "/api/v1/memory", ["memory"], _auth),
    # ⑤R F3（批10）：settings 族原挂载（原 main.py L485/L500/L503）——settings 45 端点
    # （llm-options=H5 chat 依赖/chat-attachments/document-parsing/network/tour 等）+
    # capabilities_settings（能力开关）+ mcp_settings（MCP 配置）——活探 404→真缺口闭合
    (capabilities_settings.router, "/api/v1/capabilities", ["capabilities"], _auth),
    (settings.router, "/api/v1/settings", ["settings"], _auth),
    (mcp_settings.router, "/api/v1/settings/mcp", ["mcp-settings"], None),
    # ⑤R R2（批13）A1 对拍闭合：原仓挂载表全量补齐（L433-L558 逐对形状——vendor 件在盘
    # 未装配的 R1 残余缺口，A1 全量重放 404→契约等值）。chat/auth 不在此列：tupu 自有
    # chat.router（/api/v1，主表 L154「DT chat 引擎不搬」）与 ⑥-2a auth 面已承接同前缀面。
    (multi_user_router, "/api/v1/multi-user", ["multi-user"], _auth),          # 原 L433
    (co_writer.router, "/api/v1/co_writer", ["co_writer"], _auth),             # 原 L476
    (space_mcp.router, "/api/v1/space/mcp", ["space-mcp"], _auth),             # 原 L512
    (space_cli_apps.router, "/api/v1/space/cli-apps", ["space-cli-apps"], _auth),  # 原 L522
    (skills.router, "/api/v1/skills", ["skills"], _auth),                      # 原 L528
    (subagents.router, "/api/v1/subagents", ["subagents"], _auth),             # 原 L529
    (personas.router, "/api/v1/personas", ["personas"], _auth),                # 原 L532
    (tools_router.router, "/api/v1/tools", ["tools"], _auth),                  # 原 L535
    (system.router, "/api/v1/system", ["system"], _auth),                      # 原 L536
    (plugins_api.router, "/api/v1/plugins", ["plugins"], _auth),               # 原 L544
    (agent_config.router, "/api/v1/agent-config", ["agent-config"], _auth),    # 原 L547
    (partners.router, "/api/v1/partners", ["partners"], _admin),               # 原 L550（_admin）
    (attachments.router, "/api/attachments", ["attachments"], _auth),          # 原 L553（前缀无 /v1）
    # 引擎批6 6.3：unified_ws.router 卸挂（原 L118=L562）——统一 WS 退役，对话面走桥
    # POST /api/v2/skills/capability SSE；vendor 树物理文件保留（裁定点 A——A4 基线不破坏）。
    # ⑤R R2（批13）A1 二轮：auth/chat 两族补挂（原 L421/L440 无 deps）——同前缀 tupu 自有
    # 路由（⑥-2a auth 面/chat 引擎）先注册恒优先，vendor 件仅补 tupu 缺位路径
    # （auth/status、auth/profile、chat/sessions 等），同路径不遮蔽自有面=合并裁定承接。
    (auth_router.router, "/api/v1/auth", ["auth"], None),                      # 原 L421（public）
    (chat_router.router, "/api/v1", ["chat"], _auth),                          # 原 L440
]


def static_mounts():
    """原仓 main.py L342-376 静态挂载——workspace 根走 DEEPTUTOR_HOME（接线点2 env 单点）。

    返回 [(mount_path, directory, name)]；B1 域=母题库图片+教材页图+年级资源×2。"""
    from fastapi.staticfiles import StaticFiles  # noqa: F401（挂载方使用）
    from app.services.sishu_full.services.path_service import get_path_service

    ws = get_path_service().get_workspace_dir()
    out = []
    for rel, name in [
        ("mother_questions/images", "mother-question-images"),
        ("curriculum/pages", "curriculum-pages"),
        ("grade7", "grade7-resources"),
        ("grade3", "grade3-resources"),
    ]:
        d = ws / rel
        d.mkdir(parents=True, exist_ok=True)
        out.append(({"mother_questions/images": "/api/v1/mother-questions/files",
                     "curriculum/pages": "/api/v1/curriculum/pages",
                     "grade7": "/api/v1/grade7",
                     "grade3": "/api/v1/grade3"}[rel], d, name))
    return out
