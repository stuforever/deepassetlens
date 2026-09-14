# -*- coding: utf-8 -*-
"""记忆插槽②（spec §五/§八）：/memory/ 路由换心脏——物理树持久化适配器。

双根读（先用户根 miss 专家根——手册在专家根）；单根写（仅用户根，专家根写即拒
——手册防改第二道锁）；写前 backup/{ts}/ 轮转 3 版（投毒/误写恢复通道）；写成功
落 expert_events kind=memory_write（agent_edit 台账，spec §八）。根经
memory_runtime ContextVar 运行时解析。读失败=文件视为不存在（不阻装配）；
写失败=工具报错如实上屏（spec §十一）。
"""
import datetime as _dt
import logging
import shutil
from pathlib import Path
from typing import Any, Dict

from deepagents.backends.protocol import (
    DeleteResult, EditResult, FileDownloadResponse, LsResult, PERMISSION_DENIED, ReadResult, WriteResult)
from deepagents.backends.utils import create_file_data

from app.services.expert_paths import memory_expert_root, memory_user_root
from app.services.memory_runtime import current as _current_runtime
from app.services.memory_slots import normalize_memory_field

logger = logging.getLogger(__name__)
_MEMORY_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "memory"
_BACKUP_KEEP = 3


def _safe_join(root: Path, rel: str) -> Path:
    """路径穿越防护：resolve 后必须落 root 内（管理页 file 端点同款铁则）。"""
    p = (root / rel).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ValueError(f"路径越界: {rel}")
    return p


def _virtual_rel(virtual_path: str) -> str:
    """树内相对路径解析。兼容两形态（批2 实证修正 #2）：
    - 完整虚拟路径 "/memory/AGENTS.md"（MemoryTreeBackend 直调/单测）；
    - Composite 分发的 stripped 相对路径 "AGENTS.md"（_get_backend_and_key 已去前缀——
      composite.read/adownload_files 等全家均传 stripped_key，实测）。
    其余绝对路径（/etc/passwd 等）= 域外，拒。"""
    p = str(virtual_path or "").strip()
    if p.startswith("/memory/"):
        return p[len("/memory/"):] or "."
    if p.startswith("/"):
        raise ValueError(f"MemoryTreeBackend 域外路径: {p}")
    return p or "."


class MemoryTreeBackend:
    """~Backend 协议适配器（read/write/edit/ls 核心四法；delete/grep/glob/upload/download
    明示不支持——记忆只增不删走管理页将来工具，spec §九 YAGNI 裁剪）。"""

    def __init__(self, expert_id: str, card: Dict[str, Any]):
        self.expert_id = expert_id
        _mem = normalize_memory_field((card or {}).get("memory"))
        self._legacy = [p for p in _mem["legacy_paths"]]
        self._writable = {s["path"] for s in _mem["slots"]
                          if s.get("type") == "RAW_MD" and s.get("writer") == "agent_edit"}
        self._slot_by_path = {s["path"]: s for s in _mem["slots"]}

    def _roots(self):
        rt = _current_runtime()
        return (memory_user_root(self.expert_id, rt["user"]),
                memory_expert_root(self.expert_id))

    # ---- 读：双根叠加 ----
    def read(self, file_path: str, offset: int = 0, limit: int = 2000):
        try:
            uref, eroot = self._roots()
            rel = _virtual_rel(file_path)
            for root in (uref, eroot):                      # 先用户根，miss 专家根
                p = _safe_join(root, rel)
                if p.is_file():
                    text = p.read_text("utf-8", errors="replace")
                    lines = text.splitlines(keepends=True)[offset:offset + limit]
                    return ReadResult(file_data=create_file_data("".join(lines)))
            return ReadResult(error=f"File '{file_path}' not found")
        except Exception as e:
            logger.warning(f"[MemoryTree] 读失败视为不存在: {file_path} {e}")
            return ReadResult(error=f"File '{file_path}' not found")

    # ---- 写：仅用户根 + 双锁 + 备份 + 台账 ----
    def write(self, file_path: str, content: str):
        try:
            uref, eroot = self._roots()
            rel = _virtual_rel(file_path)
            vpath = "/memory/" + rel      # 归一完整虚拟路径再对卡声明集合（stripped 兼容，批2 实证修正 #2）
            if (eroot / rel).resolve().is_file() or vpath in self._legacy:
                return WriteResult(error=f"{PERMISSION_DENIED}: 专家手册只读（MemoryTree 第二道锁）")
            if vpath not in self._writable:
                return WriteResult(error=f"{PERMISSION_DENIED}: 未声明的可写槽: {vpath}")
            target = _safe_join(uref, rel)
            self._backup_before_write(uref, rel, target)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self._record_write(vpath, content, mode="write")
            return WriteResult(path=vpath)
        except Exception as e:
            logger.warning(f"[MemoryTree] 写失败如实上屏: {file_path} {e}")
            return WriteResult(error=str(e))

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False):
        cur = self.read(file_path, 0, 10 ** 9)
        # 结果对象全 @dataclass（deepagents.backends.protocol 实测）——属性访问 r.error/r.file_data
        # （计划 R2 第3条「纯 dict 键访问」为误诊，实证修正：ReadResult 等有 __post_init__ 的 dataclass）。
        if cur.error:
            return EditResult(error=cur.error)
        text = (cur.file_data or {}).get("content", "")
        if old_string not in text:
            return EditResult(error=f"Error: old_string not found in '{file_path}'")
        new_text = text.replace(old_string, new_string) if replace_all else \
            text.replace(old_string, new_string, 1)
        w = self.write(file_path, new_text)
        if w.error:
            return EditResult(error=w.error)
        return EditResult(path=file_path, occurrences=text.count(old_string))

    def ls(self, path: str):
        try:
            uref, eroot = self._roots()
            rel = _virtual_rel(path)
            rel_disp = "" if rel == "." else rel.rstrip("/") + "/"   # "."（树根）不产生 "/memory//" 双斜杠
            entries = []
            for root in (uref, eroot):
                base = _safe_join(root, rel)
                if base.is_dir():
                    for p in sorted(base.iterdir()):
                        entries.append({"path": f"/memory/{rel_disp}{p.name}" if p.is_file()
                                        else f"/memory/{rel_disp}{p.name}/",
                                        "is_dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0,
                                        "modified_at": ""})
            return LsResult(entries=entries)
        except Exception as e:
            return LsResult(entries=[])

    def delete(self, file_path: str):
        return DeleteResult(error="记忆树禁删（②期只增不删——在线编辑/删除工具 spec §九 YAGNI 明示不做）")

    def grep(self, *a, **k):
        raise NotImplementedError("记忆树 grep 未接线（read_file 已覆盖查询场景）")

    def glob(self, *a, **k):
        raise NotImplementedError("记忆树 glob 未接线")

    # ---- async 面（CompositeBackend 分发全家实证：aread/awrite/aedit/als/adelete/adownload_files）----
    # 物理文件读快，同步直调不引线程池（memory_trace「锁内直写」同款裁决）。
    # 批2 实证缺陷：MemoryMiddleware.before_agent 走 adownload_files 注入 memory sources——
    # 缺此方法 CompositeBackend AttributeError（e2e 362s/0 表事故根因）。
    async def aread(self, file_path: str, offset: int = 0, limit: int = 2000):
        return self.read(file_path, offset, limit)

    async def awrite(self, file_path: str, content: str):
        return self.write(file_path, content)

    async def aedit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False):
        return self.edit(file_path, old_string, new_string, replace_all)

    async def als(self, path: str):
        return self.ls(path)

    async def adelete(self, file_path: str):
        return self.delete(file_path)

    async def adownload_files(self, paths: list):
        """批量下载（MemoryMiddleware 注入走此入口）：成功=文件 bytes，失败=error。"""
        out = []
        for p in paths:
            r = self.read(p, 0, 10 ** 9)
            if r.error:
                out.append(FileDownloadResponse(path=p, content=None, error="file_not_found"))
            else:
                content = (r.file_data or {}).get("content", "")
                out.append(FileDownloadResponse(
                    path=p,
                    content=content.encode("utf-8") if isinstance(content, str) else content,
                    error=None))
        return out

    # ---- 内部 ----
    def _backup_before_write(self, uref: Path, rel: str, target: Path) -> None:
        if not target.is_file():
            return
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        bdir = uref / "backup" / ts
        bdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, bdir / target.name)
        backups = sorted((uref / "backup").iterdir())
        for old in backups[:-_BACKUP_KEEP]:               # 轮转保留最近 3 版
            shutil.rmtree(old, ignore_errors=True)

    def _record_write(self, file_path: str, content: str, *, mode: str) -> None:
        try:                                              # fire-and-forget（spec §十一）
            from app.services import expert_config as _ec
            from app.services.memory_runtime import current as _cur
            rt = _cur()
            slot = self._slot_by_path.get(file_path, {})
            _ec.record_event(self.expert_id, "memory_write", detail={
                "user": rt["user"], "slot": slot.get("slot"), "path": file_path,
                "bytes": len(content.encode("utf-8")), "mode": mode})
        except Exception as e:
            logger.warning(f"[MemoryTree] memory_write 台账失败(不阻塞): {e}")


# ---- 目录骨架 + RAW_MD 预创建 + AGENTS.md 受控搬迁（启动序列，spec §九步骤2）----

def ensure_dirs(expert_id: str, card: Dict[str, Any], user: str = "anonymous") -> None:
    """骨架幂等创建 + RAW_MD 槽文件预创建（头 `# {槽名}\\n`——保证 edit_file 永远对
    存在文件工作）。失败不阻启动（spec §十一：目录缺了下次再建）。"""
    try:
        _mem = normalize_memory_field((card or {}).get("memory"))
        uref = memory_user_root(expert_id, user)
        for s in _mem["slots"]:
            if s.get("type") == "L1_TRACE":
                (uref / "trace" / (s.get("surface") or "chat")).mkdir(parents=True, exist_ok=True)
        for s in _mem["slots"]:
            if s.get("type") == "RAW_MD":
                p = _safe_join(memory_user_root(expert_id, user), _virtual_rel(s["path"]))
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.write_text(f"# {s.get('slot') or s['path']}\n", encoding="utf-8")
        (uref / "backup").mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"[MemoryTree] ensure_dirs 失败(下次再建): {e}")


def _migrate_agents_md() -> None:
    """AGENTS.md 受控搬迁（spec §九步骤2）：平台根→wenshu/AGENTS.md。前后校验和逐字节
    比对；旧位留 .bak；幂等（目标已存在且校验同→跳过）；失败 fail-fast（等值前提
    被破坏时宁可不起——runbook 明示）。"""
    import hashlib
    src = _MEMORY_ROOT / "AGENTS.md"
    dst = _MEMORY_ROOT / "wenshu" / "AGENTS.md"
    if dst.exists():
        if src.exists():
            if hashlib.sha256(src.read_bytes()).hexdigest() == \
                    hashlib.sha256(dst.read_bytes()).hexdigest():
                return                                     # 幂等：目标在+内容同
            raise RuntimeError("AGENTS.md 搬迁冲突：平台根与专家根内容不一致，拒自动处理")
        return
    if not src.exists():
        return                                             # 新库：无可搬
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dst.write_bytes(data)                                  # 逐字节写
    if hashlib.sha256(dst.read_bytes()).hexdigest() != hashlib.sha256(data).hexdigest():
        raise RuntimeError("AGENTS.md 搬迁校验和不等（fail-fast）")
    shutil.copy2(src, _MEMORY_ROOT / "AGENTS.md.bak")       # 旧位留 .bak
    logger.info("[MemoryTree] AGENTS.md 受控搬迁完成（校验和逐字节等值，旧位留 .bak）")
