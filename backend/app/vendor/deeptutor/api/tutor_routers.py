# -*- coding: utf-8 -*-
"""⑤R B1（唯一交棒 批3.1）：tutor_routers——原仓 main.py 挂载表的 B1 域子集（派生接线件）。

对拍锚：每对 (router, prefix, tags) 与原仓 main.py L463-475 逐字一致；
deps=接线点1 shim（require_auth 同名同形，背靠 tupu core/auth + expert ACL 统一门）。
随批次增长登记：B1=curriculum/mother_question+静态挂载；B2+=question/book/... 逐批追加。"""
from fastapi import Depends

# 原导入路径零改码（vendor 子树原结构）
from deeptutor.api.routers.auth import require_auth as _dt_require_auth  # noqa: E402

# 原仓 main.py `_auth = [Depends(require_auth)]` 的同位接线（指 vendor 内 auth 模块）：
# Header/Cookie 形签名对 WS 路由可解（原仓注释即为此设计）；AUTH_ENABLED=false 时放行
# 并安装桌面语义用户——与 dt_auth_shim 在 auth=0 下行为等价；auth=1 实测项归批18/20.2/20.3。
_auth = [Depends(_dt_require_auth)]

# 原导入路径零改码（vendor 子树原结构）
from deeptutor.api.routers import mother_question  # noqa: E402
from deeptutor.api.routers import knowledge as knowledge_router  # noqa: E402
from deeptutor.api.routers import question, quiz_judge  # noqa: E402
from deeptutor.learning.curriculum import router as curriculum_router  # noqa: E402

tutor_routers = [
    (mother_question.router, "/api/v1/mother-questions", ["mother-questions"], _auth),
    (curriculum_router, "/api/v1/curriculum", ["curriculum"], _auth),
    # ⑤R B1 3.2：knowledge 域原形状路由（契约适配层见 app/api/dt_knowledge_adapter.py——
    # 形状由本路由 1:1 提供；④挂接=注册表镜像+tutor 卡 knowledge_sources）
    (knowledge_router.router, "/api/v1/knowledge", ["knowledge"], _auth),
    # ⑤R B2：问答判题练习件——question(WS mimic/generate)+quiz_judge(WS judge)
    # 原挂载（原仓 main.py L442/L566）：question 带 _auth，quiz_judge 自带 ws_require_auth
    (question.router, "/api/v1/question", ["question"], _auth),
    (quiz_judge.router, "/api/v1", ["quiz-judge"], None),
]


def static_mounts():
    """原仓 main.py L342-376 静态挂载——workspace 根走 DEEPTUTOR_HOME（接线点2 env 单点）。

    返回 [(mount_path, directory, name)]；B1 域=母题库图片+教材页图+年级资源×2。"""
    from fastapi.staticfiles import StaticFiles  # noqa: F401（挂载方使用）
    from deeptutor.services.path_service import get_path_service

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
