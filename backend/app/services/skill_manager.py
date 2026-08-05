"""
技能管理 Service 层
基于新数据模型 (Skill, SkillVersion, SkillExecLog)
五件套文件系统存储
"""

import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import OperationalError

from app.models.skill import Skill, SkillVersion, SkillExecLog, SkillApiBinding
from app.core.skill_storage import get_skill_storage

INLINE_SOURCE_KEYS = {
    "script",
    "sql",
    "prompt",
    "steps",
    "method",
    "url",
    "headers",
    "body_template",
    "auth",
}


def _build_lightweight_version_content(storage, skill_type: str, version_str: str, content: Dict[str, Any]) -> Dict[str, Any]:
    stored_content = {
        "schema_version": str(content.get("schema_version") or "1.0"),
        "storage_type": "filesystem",
        "entrypoint": f"scripts/main.{storage._ext_for_type(skill_type)}",
        "version": version_str,
    }
    for extra_key in [
        "debug_examples",
        "display_config",
        "input_example",
        "output_example",
        "step_examples",
        "snapshot_path",
    ]:
        if extra_key in content:
            stored_content[extra_key] = content.get(extra_key)
    return stored_content


def _persist_skill_source_to_filesystem(storage, skill_code: str, skill_type: str, content: Dict[str, Any]) -> None:
    if skill_type == "python":
        script = content.get("script", "")
        if script:
            storage.write_file(skill_code, "scripts/main.py", script)
    elif skill_type == "sql":
        sql = content.get("sql", "")
        if sql:
            storage.write_file(skill_code, "scripts/main.sql", sql)
    elif skill_type == "natural":
        prompt = content.get("prompt", "")
        if prompt:
            storage.write_file(skill_code, "scripts/main.txt", prompt)
    elif skill_type == "http":
        http_config = {
            "method": content.get("method", "GET"),
            "url": content.get("url", ""),
            "headers": content.get("headers", {}),
            "body_template": content.get("body_template", ""),
            "auth": content.get("auth", {}),
        }
        if any(http_config.values()):
            storage.write_file(skill_code, "scripts/main.yaml", json.dumps(http_config, indent=2, ensure_ascii=False))
    elif skill_type == "mixed":
        steps = content.get("steps", [])
        if steps:
            storage.write_file(skill_code, "scripts/main.yaml", json.dumps({"steps": steps}, indent=2, ensure_ascii=False))

    # 清除 SkillRunnable 的模块缓存，让下次调用重新加载
    try:
        from app.services.skill_runnable import _MODULE_CACHE
        if skill_code in _MODULE_CACHE:
            del _MODULE_CACHE[skill_code]
            logger.info(f"[skill_manager] 已清除 SkillRunnable 模块缓存: {skill_code}")
    except ImportError:
        pass


def _contains_inline_source(content: Dict[str, Any]) -> bool:
    return any(key in (content or {}) for key in INLINE_SOURCE_KEYS)


def _norm36(val):
    s = str(val).strip()
    if len(s) == 32:
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


class SkillService:
    """技能主表服务"""

    @staticmethod
    def generate_skill_code(name: str) -> str:
        """生成技能代码（转为小写，支持大小写不敏感）"""
        import re
        code = re.sub(r'[^\w\s-]', '', name).strip()
        code = re.sub(r'[-\s]+', '_', code)
        return code.lower()[:100]

    @staticmethod
    def create_skill(db: Session, data: Dict[str, Any]) -> Skill:
        """创建技能 + 五件套目录骨架"""
        skill_code = data.get("skill_code")
        if not skill_code:
            skill_code = SkillService.generate_skill_code(data["name"])

        # 检查 skill_code 是否已存在（大小写不敏感）
        existing = db.query(Skill).filter(
            Skill.skill_code == skill_code
        ).first()
        if existing:
            raise ValueError(f"技能代码 '{skill_code}' 已存在")

        # 创建五件套文件系统目录
        storage = get_skill_storage()
        try:
            storage.create_skeleton(skill_code, {
                "name": data["name"],
                "description": data.get("description", ""),
                "skill_type": data.get("skill_type", "natural"),
            })
        except FileExistsError:
            pass  # 目录已存在，继续

        skill = Skill(
            skill_code=skill_code,
            name=data["name"],
            description=data.get("description"),
            skill_type=data.get("skill_type", "natural"),
            status=data.get("status", "draft"),
            storage_path=str(storage._skill_path(skill_code)),
            tags=data.get("tags", []),
            priority=data.get("priority", 0),
            timeout=data.get("timeout", 30),
            retry_policy=data.get("retry_policy", {"max_retries": 0, "retry_delay": 1}),
            resource_limits=data.get("resource_limits", {"memory_mb": 512, "timeout_seconds": 30}),
            permissions=data.get("permissions", {"network": True, "filesystem": False, "shell": False, "risk_level": "low", "allowed_env": []}),
            app_type=data.get("app_type"),
            target_menu=data.get("target_menu"),
            workspace_id=data.get("workspace_id"),
            created_by=data.get("created_by"),
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def get_skill(db: Session, skill_id) -> Optional[Skill]:
        sid = str(skill_id)
        if len(sid) == 32:
            sid = f"{sid[:8]}-{sid[8:12]}-{sid[12:16]}-{sid[16:20]}-{sid[20:]}"
        return db.query(Skill).filter(Skill.skill_id == sid).first()

    @staticmethod
    def get_skill_by_code(db: Session, skill_code: str) -> Optional[Skill]:
        return db.query(Skill).filter(Skill.skill_code == skill_code.lower()).first()

    @staticmethod
    def list_skills(db: Session, status: Optional[str] = None, skill_type: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Skill]:
        query = db.query(Skill)
        if status:
            query = query.filter(Skill.status == status)
        if skill_type:
            query = query.filter(Skill.skill_type == skill_type)
        return query.order_by(Skill.priority.asc(), Skill.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_skill(db: Session, skill_id, data: Dict[str, Any]) -> Skill:
        skill = SkillService.get_skill(db, skill_id)
        if not skill:
            raise ValueError("技能不存在")

        for field in ["name", "description", "skill_type", "status", "tags", "priority", "timeout", "retry_policy", "resource_limits", "permissions", "app_type", "target_menu"]:
            if field in data:
                setattr(skill, field, data[field])

        skill.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def delete_skill(db: Session, skill_id):
        skill = SkillService.get_skill(db, skill_id)
        if not skill:
            raise ValueError("技能不存在")
        sid = _norm36(skill_id)
        from app.core.skill_storage import get_skill_storage
        storage = get_skill_storage()
        storage.delete_skill_package(skill.skill_code)
        # 手动级联删除：先删 exec_logs，再删 versions，最后删 skill
        # SQLite + SQLAlchemy 外键级联行为不可靠，必须手动处理
        from app.models.skill import SkillExecLog, SkillVersion
        db.query(SkillExecLog).filter(SkillExecLog.skill_id == sid).delete(synchronize_session=False)
        db.query(SkillVersion).filter(SkillVersion.skill_id == sid).delete(synchronize_session=False)
        db.flush()
        db.delete(skill)
        db.commit()


class VersionService:
    """技能版本服务"""

    @staticmethod
    def create_version(db: Session, skill_id, data: Dict[str, Any]) -> SkillVersion:
        """创建新版本：内容写入文件系统，数据库仅存元数据和文件引用"""
        sid = _norm36(skill_id)
        skill = SkillService.get_skill(db, sid)
        if not skill:
            raise ValueError("技能不存在")

        version_str = data.get("version", "1.0.0")

        # 检查版本号是否已存在
        existing = db.query(SkillVersion).filter(
            SkillVersion.skill_id == sid,
            SkillVersion.version == version_str
        ).first()
        if existing:
            raise ValueError(f"版本 '{version_str}' 已存在")

        # 写入文件系统
        storage = get_skill_storage()
        skill_code = skill.skill_code
        content = data.get("content", {})

        _persist_skill_source_to_filesystem(storage, skill_code, skill.skill_type, content)
        if skill.skill_type == "python":
            deps = content.get("dependencies", {})
            pip_deps = deps.get("pip", []) if isinstance(deps, dict) else []
            if pip_deps:
                storage.write_file(skill_code, "requirements.txt", "\n".join(pip_deps))

        # 写入 schema 到 assets/
        input_schema = data.get("input_schema", {"type": "object", "properties": {}, "required": []})
        output_schema = data.get("output_schema", {"type": "object", "properties": {}})
        storage.set_schema(skill_code, "input", input_schema)
        storage.set_schema(skill_code, "output", output_schema)

        # 数据库仅存储元数据和轻量级引用
        stored_content = _build_lightweight_version_content(storage, skill.skill_type, version_str, content)

        version = SkillVersion(
            skill_id=sid,
            version=version_str,
            status="draft",
            # schema 仍存在数据库用于快速检索，但文件系统有权威副本
            input_schema=input_schema,
            output_schema=output_schema,
            # content 改为轻量级文件引用信息
            content=stored_content,
            dependencies=data.get("dependencies", {"pip": [], "apt": [], "env_vars": {}}),
            changelog=data.get("changelog"),
            created_by=data.get("created_by"),
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def normalize_all_versions_to_filesystem(db: Session) -> int:
        storage = get_skill_storage()
        skills = {str(item.skill_id): item for item in db.query(Skill).all()}
        changed = 0
        for version in db.query(SkillVersion).all():
            skill = skills.get(str(version.skill_id))
            if not skill:
                continue
            content = version.content if isinstance(version.content, dict) else {}
            if not _contains_inline_source(content):
                continue
            version.content = _build_lightweight_version_content(storage, skill.skill_type, version.version, content)
            changed += 1
        if changed:
            db.commit()
        return changed

    @staticmethod
    def publish_version(db: Session, version_id, released_by: str) -> SkillVersion:
        """发布版本（合并激活操作）"""
        vid = _norm36(version_id)
        version = db.query(SkillVersion).filter(SkillVersion.version_id == vid).first()
        if not version:
            raise ValueError("版本不存在")

        if version.status != "draft":
            raise ValueError("只有 draft 状态可以发布")

        # 将该技能的其他 active 版本改为 archived
        db.query(SkillVersion).filter(
            SkillVersion.skill_id == version.skill_id,
            SkillVersion.status == "active"
        ).update({"status": "archived"}, synchronize_session=False)

        # 发布当前版本
        version.status = "active"
        version.released_by = released_by
        version.released_at = datetime.utcnow()

        # 更新 Skill 主表的 current_version_id
        skill = SkillService.get_skill(db, version.skill_id)
        skill.current_version_id = version.version_id
        skill.status = "published"

        # 6.2 版本发布时自动物理快照归档
        try:
            storage = get_skill_storage()
            zip_path = storage.export_zip(skill.skill_code)
            import shutil
            from pathlib import Path
            archive_dir = Path(storage.root) / "archives" / skill.skill_code
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_name = f"v{version.version}_{zip_path.name}"
            archive_path = archive_dir / archive_name
            shutil.move(str(zip_path), str(archive_path))
            if isinstance(version.content, dict):
                version.content["snapshot_path"] = str(archive_path)
        except Exception:
            pass

        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def get_version(db: Session, version_id) -> Optional[SkillVersion]:
        vid = str(version_id)
        if len(vid) == 32:
            vid = f"{vid[:8]}-{vid[8:12]}-{vid[12:16]}-{vid[16:20]}-{vid[20:]}"
        return db.query(SkillVersion).filter(SkillVersion.version_id == vid).first()

    @staticmethod
    def list_versions(db: Session, skill_id, status: Optional[str] = None) -> List[SkillVersion]:
        sid = str(skill_id)
        if len(sid) == 32:
            sid = f"{sid[:8]}-{sid[8:12]}-{sid[12:16]}-{sid[16:20]}-{sid[20:]}"
        query = db.query(SkillVersion).filter(SkillVersion.skill_id == sid)
        if status:
            query = query.filter(SkillVersion.status == status)
        return query.order_by(desc(SkillVersion.created_at)).all()

    @staticmethod
    def archive_version(db: Session, version_id) -> SkillVersion:
        """归档版本"""
        version = VersionService.get_version(db, version_id)
        if not version:
            raise ValueError("版本不存在")
        version.status = "archived"
        db.commit()
        db.refresh(version)
        return version


class ExecutionService:
    """执行服务"""

    @staticmethod
    def create_execution(db: Session, skill_id, version_id, input_data: Dict[str, Any], created_via: str = "manual", is_debug: bool = False) -> SkillExecLog:
        """创建执行记录"""
        execution_code = f"exec_{uuid.uuid4().hex[:12]}" if not is_debug else f"dbg_{uuid.uuid4().hex[:12]}"
        sid = _norm36(skill_id) if skill_id else None
        vid = _norm36(version_id) if version_id else None

        log = SkillExecLog(
            skill_id=sid,
            version_id=vid,
            execution_code=execution_code,
            input_data=input_data,
            status="running",
            created_via=created_via,
            is_debug=is_debug,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def complete_execution(db: Session, execution_code: str, output_data: Optional[Dict[str, Any]], error_message: Optional[str], duration_ms: int):
        """完成执行"""
        log = db.query(SkillExecLog).filter(SkillExecLog.execution_code == execution_code).first()
        if not log:
            raise ValueError("执行记录不存在")

        log.status = "failed" if error_message else "success"
        log.output_data = output_data
        log.error_message = error_message
        log.duration_ms = duration_ms
        log.completed_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def get_execution(db: Session, execution_code: str) -> Optional[SkillExecLog]:
        return db.query(SkillExecLog).filter(SkillExecLog.execution_code == execution_code).first()

    @staticmethod
    def list_executions(db: Session, skill_id: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[SkillExecLog]:
        query = db.query(SkillExecLog)
        if skill_id:
            query = query.filter(SkillExecLog.skill_id == _norm36(skill_id))
        if status:
            query = query.filter(SkillExecLog.status == status)
        try:
            return query.order_by(desc(SkillExecLog.started_at)).offset(skip).limit(limit).all()
        except OperationalError:
            # 某些旧库在 skill_id + started_at 上缺少组合索引，先降级为不排序查询兜底，避免历史页直接 500
            return query.offset(skip).limit(limit).all()


class SkillApiBindingService:
    """技能对应的 API 绑定服务"""

    @staticmethod
    def list_bindings(db: Session, skill_id: Optional[str] = None, enabled: Optional[bool] = None) -> List[SkillApiBinding]:
        query = db.query(SkillApiBinding)
        if skill_id:
            query = query.filter(SkillApiBinding.skill_id == _norm36(skill_id))
        if enabled is not None:
            query = query.filter(SkillApiBinding.enabled == bool(enabled))
        return query.order_by(desc(SkillApiBinding.created_at)).all()

    @staticmethod
    def get_binding(db: Session, binding_id) -> Optional[SkillApiBinding]:
        return db.query(SkillApiBinding).filter(SkillApiBinding.binding_id == _norm36(binding_id)).first()

    @staticmethod
    def upsert_binding(db: Session, skill_id, data: Dict[str, Any]) -> SkillApiBinding:
        sid = _norm36(skill_id)
        api_code = str(data.get("api_code") or "").strip()
        if not api_code:
            raise ValueError("api_code不能为空")
        binding = db.query(SkillApiBinding).filter(
            SkillApiBinding.skill_id == sid,
            SkillApiBinding.api_code == api_code,
        ).first()
        if not binding:
            binding = SkillApiBinding(
                skill_id=sid,
                api_code=api_code,
                api_name=data.get("api_name") or api_code,
                api_type=data.get("api_type") or "capability",
                provider_type=data.get("provider_type") or "internal",
                target_ref=data.get("target_ref") or "",
                version_id=_norm36(data["version_id"]) if data.get("version_id") else None,
                enabled=bool(data.get("enabled", True)),
                timeout_seconds=int(data.get("timeout_seconds") or 30),
                retry_policy=data.get("retry_policy") or {"max_retries": 0, "retry_delay": 1},
                auth_mode=data.get("auth_mode"),
                route_config=data.get("route_config"),
                remark=data.get("remark"),
                created_by=data.get("created_by"),
                updated_by=data.get("updated_by"),
            )
            db.add(binding)
        else:
            for field in ["api_name", "api_type", "provider_type", "target_ref", "auth_mode", "route_config", "remark", "created_by", "updated_by"]:
                if field in data:
                    setattr(binding, field, data[field])
            if "version_id" in data:
                binding.version_id = _norm36(data["version_id"]) if data.get("version_id") else None
            if "enabled" in data:
                binding.enabled = bool(data.get("enabled"))
            if "timeout_seconds" in data:
                binding.timeout_seconds = int(data.get("timeout_seconds") or 30)
            if "retry_policy" in data:
                binding.retry_policy = data.get("retry_policy") or {"max_retries": 0, "retry_delay": 1}
            binding.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(binding)
        return binding

    @staticmethod
    def delete_binding(db: Session, binding_id) -> None:
        binding = SkillApiBindingService.get_binding(db, binding_id)
        if not binding:
            raise ValueError("绑定不存在")
        db.delete(binding)
        db.commit()
