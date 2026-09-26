"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
# -*- coding: utf-8 -*-
from fastapi import Depends

# 原导入路径零改码（vendor 子树原结构）
from app.services.sishu_full.api.routers import chat as chat_router  # noqa: E402

# 原仓 main.py `_auth = [Depends(require_auth)]` 的同位接线。
# 权限重构T6.1（design §7 批1）：换轨平台依赖——require_expert("use","sishu") 执法
# + 平台→vendor ContextVar 桥（platform_require_auth，path_service 分目录语义不变）。
# 权限重构T6批3：vendor routers/auth 物理删除——桥迁 vendor_bridge（require_auth/
# require_admin vendor JWT 流随之退役，身份源=平台 AuthMiddleware/平台 JWT）。
from app.services.sishu_full.api.vendor_bridge import codex_callback_router  # noqa: E402
from app.services.sishu_full.api.vendor_bridge import platform_require_auth  # noqa: E402

_auth = [Depends(platform_require_auth)]

# 原导入路径零改码（vendor 子树原结构）
from app.services.sishu_full.api.routers import knowledge as knowledge_router  # noqa: E402
from app.services.sishu_full.api.routers import (  # noqa: E402
    co_writer,
    partners,
    skills,
    subagents,
    tools as tools_router,
)
# 切换 R5（§四 删除面）：已卸挂路由族（_SISHU_BATCH6_UNMOUNTED 全集）vendor 文件
# 物理删除——死导入同步摘除。存活挂载仅余本表行（平台承接面在 app/main.py 注册）。
from app.services.sishu_full.api.routers import (  # noqa: E402
    settings,
)
from app.services.sishu_full.multi_user.router import router as multi_user_router  # noqa: E402
# 权限重构T6.1：_admin 换轨 require_permission("sishu","manage")（桥接同上）。
from app.services.sishu_full.api.vendor_bridge import platform_require_admin  # noqa: E402
from app.services.sishu_full.learning.curriculum import router as curriculum_router  # noqa: E402

# 原仓 main.py L551 `_admin = [Depends(require_admin)]`（partners 域——管理面路由族）
_admin = [Depends(platform_require_admin)]

tutor_routers = [
    (curriculum_router, "/api/v1/curriculum", ["curriculum"], _auth),
    # ⑤R B1 3.2：knowledge 域原形状路由（契约适配层见 app/api/dt_knowledge_adapter.py——
    # 形状由本路由 1:1 提供；④挂接=注册表镜像+tutor 卡 knowledge_sources）
    (knowledge_router.router, "/api/v1/knowledge", ["knowledge"], _auth),
    # ⑤R F3（批10）：settings 族原挂载（原 main.py L485/L500/L503）——settings 45 端点
    # （llm-options=H5 chat 依赖/chat-attachments/document-parsing/network/tour 等）
    # （capabilities_settings/mcp_settings 两行原在其前——R5 已删，相对次序保持）
    (settings.router, "/api/v1/settings", ["settings"], _auth),
    # ⑤R R2（批13）A1 对拍闭合：原仓挂载表全量补齐（L433-L558 逐对形状——vendor 件在盘
    # 未装配的 R1 残余缺口，A1 全量重放 404→契约等值）。chat/auth 不在此列：tupu 自有
    # chat.router（/api/v1，主表 L154「DT chat 引擎不搬」）与 ⑥-2a auth 面已承接同前缀面。
    (multi_user_router, "/api/v1/multi-user", ["multi-user"], _auth),          # 原 L433
    (co_writer.router, "/api/v1/co_writer", ["co_writer"], _auth),             # 原 L476
    (skills.router, "/api/v1/skills", ["skills"], _auth),                      # 原 L528
    (subagents.router, "/api/v1/subagents", ["subagents"], _auth),             # 原 L529
    (tools_router.router, "/api/v1/tools", ["tools"], _auth),                  # 原 L535
    (partners.router, "/api/v1/partners", ["partners"], _admin),               # 原 L550（_admin）
    # 引擎批6 6.3：unified_ws.router 卸挂（原 L118=L562）——统一 WS 退役，对话面走桥
    # POST /api/v2/skills/capability SSE。
    # ⑤R R2（批13）A1 二轮：auth/chat 两族补挂（原 L421/L440 无 deps）——同前缀 tupu 自有
    # 路由（⑥-2a auth 面/chat 引擎）先注册恒优先。T6批3：vendor auth 面退役，
    # /api/v1/auth 前缀仅余 codex OAuth 回调投递点（vendor_bridge 承接）。
    (codex_callback_router, "/api/v1/auth", ["auth"], None),                   # 原 L421（public）
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
