"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

from app.services.sishu_full.services.cli_apps.models import ENTRY_POINT_RE, AppRuntime

#: Directory name under ``data``. Also the path the compose file mounts.
CLI_APPS_DIRNAME = "cli-apps"

_STATE_FILENAME = "state.json"
_APPS_DIRNAME = "apps"


def cli_apps_root() -> Path:
    """The deployment's CLI app tree. Resolved late so tests can redirect it."""
    from app.services.sishu_full.multi_user.paths import ADMIN_WORKSPACE_ROOT

    return ADMIN_WORKSPACE_ROOT / CLI_APPS_DIRNAME


def state_path() -> Path:
    return cli_apps_root() / _STATE_FILENAME


def app_dir(app_id: str) -> Path:
    """This app's own directory. *app_id* must already be catalog-validated."""
    return cli_apps_root() / _APPS_DIRNAME / app_id


def runtime_dir(app_id: str, runtime: AppRuntime) -> Path:
    """The environment root for *app_id* under *runtime*."""
    if runtime is AppRuntime.NODE:
        return app_dir(app_id) / "node"
    return app_dir(app_id) / "venv"


def bin_dir(app_id: str, runtime: AppRuntime) -> Path:
    return runtime_dir(app_id, runtime) / "bin"


def executable_path(app_id: str, runtime: AppRuntime, entry_point: str) -> Path:
    """Absolute path of *entry_point* inside this app's own bin directory.

    ``entry_point`` comes from the catalog, so it is re-validated here rather
    than only where the entry was parsed: this function is what turns it into a
    path, and a separator or a ``..`` would name a file outside the app.
    """
    if ENTRY_POINT_RE.match(entry_point) is None:
        raise ValueError(f"Unusable CLI app entry point {entry_point!r}")
    return bin_dir(app_id, runtime) / entry_point


def install_log_path(app_id: str) -> Path:
    return app_dir(app_id) / "install.log"


def ensure_root() -> Path:
    """Create the tree, owner-only. Returns the root."""
    root = cli_apps_root()
    (root / _APPS_DIRNAME).mkdir(parents=True, exist_ok=True)
    # Owner-only: nothing here is meant to be read by another account on the
    # host, and the runner reads it through a bind mount rather than as a peer.
    for path in (root, root / _APPS_DIRNAME):
        try:
            os.chmod(path, 0o700)
        except OSError:
            # A bind-mounted or foreign-owned directory may refuse the chmod;
            # the mount's own permissions then govern, which is the deployment's
            # call to make.
            pass
    return root


def abi_stamp() -> str:
    """Identifies the interpreter/platform an install is only valid for.

    A venv records an absolute path to the interpreter that created it, so one
    built by the app container runs in the sandbox runner **only** because both
    images are built from the same Python base. Recording the stamp turns a
    mismatch after an image bump into a clear refusal instead of an
    ``ImportError`` from inside somebody's chat turn.
    """
    return f"cpython-{sys.version_info.major}.{sys.version_info.minor}-{sys.platform}"


__all__ = [
    "CLI_APPS_DIRNAME",
    "abi_stamp",
    "app_dir",
    "bin_dir",
    "cli_apps_root",
    "ensure_root",
    "executable_path",
    "install_log_path",
    "runtime_dir",
    "state_path",
]
