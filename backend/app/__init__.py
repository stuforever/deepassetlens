"""应用启动前加载本地后端配置。"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


_backend_dir = Path(__file__).resolve().parent.parent
# 配置文件被 .gitignore 排除；不存在时 load_dotenv 不会报错。
load_dotenv(_backend_dir / ".env", override=False)
# 权限重构T3（design §8.2 密钥纪律）：SUPERTOKENS_API_KEY 等基建密钥在仓库根
# .env.infra——禁进 git、禁下发前端；进程 env 优先（override=False）。
load_dotenv(_backend_dir.parent / ".env.infra", override=False)
