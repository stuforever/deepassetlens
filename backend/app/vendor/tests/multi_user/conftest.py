"""Shared fixtures for the multi_user test suite.

These fixtures isolate each test under ``tmp_path`` so we never read or write
the developer's real ``data/`` or ``multi-user/`` directories. They also
provide a context manager that pushes a ``CurrentUser`` onto the contextvar
for tests that need to call user-scoped code without going through HTTP.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from deeptutor.multi_user.context import reset_current_user, set_current_user
from deeptutor.multi_user import h5 as _h5_module
from deeptutor.multi_user.models import CurrentUser, UserScope

# 「两处都必须重绑」约定（test_h5_guard.py h5_settings_root、
# tests/api/test_voice_routes.py voice_access_code_root 同款）：h5.py 在
# import 期把 paths.USERS_ROOT 绑进自己的命名空间，_load_h5_settings 按
# h5.USERS_ROOT.parent 定位访问码设置。上面这行模块导入期 import 确保 h5
# 模块在本 conftest 收集期（任何 fixture 打补丁之前）完成首次导入——否则
# 首个触发 h5 导入的测试若正处于 paths.USERS_ROOT 已打补丁状态，h5 的
# import 期绑定会捕获 tmp 路径，monkeypatch 把该毒化值当"旧值"保存、
# teardown 又还原回毒化值，跨测试泄漏（曾致 test_h5_scope 的
# h5_scope_dep 直接调用用例读到隔离 tmp 里的 access_code=1234 而红）。


@pytest.fixture
def mu_isolated_root(tmp_path, monkeypatch) -> Path:
    """Redirect every ``multi_user`` global path under ``tmp_path``.

    Also clears the ``_path_services`` cache so ``get_path_service()`` can be
    re-resolved per test without leaking instances created in earlier tests.
    """
    from deeptutor.multi_user import grants, identity, paths

    project_root = tmp_path
    admin_root = (project_root / "data").resolve()
    users_root = admin_root / "users"
    system_root = admin_root / "system"

    monkeypatch.setattr(paths, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(paths, "USERS_ROOT", users_root)
    monkeypatch.setattr(paths, "SYSTEM_ROOT", system_root)
    monkeypatch.setattr(paths, "ADMIN_WORKSPACE_ROOT", admin_root)
    monkeypatch.setattr(paths, "LEGACY_MULTI_USER_ROOT", project_root / "multi-user")
    monkeypatch.setattr(paths, "_path_services", {})
    # 「两处都必须重绑」：h5.USERS_ROOT 的 import 期绑定不随 paths.USERS_ROOT
    # 的补丁自动更新，须一并重绑到隔离根，_load_h5_settings 才不会读到开发者
    # 真实 data/user/settings/h5.json（装了访问码的环境即红）。
    monkeypatch.setattr(_h5_module, "USERS_ROOT", users_root)

    monkeypatch.setattr(identity, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(identity, "SYSTEM_ROOT", system_root)
    monkeypatch.setattr(identity, "AUTH_DIR", system_root / "auth")
    monkeypatch.setattr(identity, "USERS_FILE", system_root / "auth" / "users.json")
    monkeypatch.setattr(identity, "SECRET_FILE", system_root / "auth" / "auth_secret")
    monkeypatch.setattr(
        identity,
        "LEGACY_USERS_FILE",
        project_root / "data" / "user" / "auth_users.json",
    )
    monkeypatch.setattr(
        identity,
        "LEGACY_SECRET_FILE",
        project_root / "data" / "user" / "auth_secret",
    )

    monkeypatch.setattr(grants, "GRANTS_DIR", system_root / "grants")

    admin_root.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def make_user(mu_isolated_root):
    """Build a ``CurrentUser`` rooted under the isolated tmp_path."""

    def _make(uid: str, *, role: str = "user", username: str | None = None) -> CurrentUser:
        from deeptutor.multi_user.paths import admin_scope

        if role == "admin":
            scope = admin_scope()
        else:
            scope = UserScope(
                kind="user",
                user_id=uid,
                root=(mu_isolated_root / "data" / "users" / uid).resolve(),
            )
        return CurrentUser(
            id=uid,
            username=username or uid,
            role=role,
            scope=scope,
        )

    return _make


@pytest.fixture
def as_user(make_user):
    """Context manager that pushes a CurrentUser onto the contextvar.

    Usage:
        with as_user("u_alice", role="user"):
            ...
    """

    @contextmanager
    def _scope(uid: str, *, role: str = "user", username: str | None = None):
        token = set_current_user(make_user(uid, role=role, username=username))
        try:
            yield
        finally:
            reset_current_user(token)

    return _scope


@pytest.fixture
def seed_user(mu_isolated_root):
    """Create a user record on disk and return the resulting record dict."""

    def _seed(username: str, password: str = "password1234", role: str = "user") -> dict:
        from deeptutor.multi_user.identity import save_user
        from deeptutor.services.auth import hash_password

        return save_user(username, hash_password(password), role=role)  # type: ignore[arg-type]

    return _seed
