from sqlalchemy.orm import Session


def _sync_scenario_skills(db: Session):
    """将文件式场景剧本(scenarios/*/SKILL.md)同步到 skills 表，使其在技能管理页可见。

    SkillManagerV2 调 GET /api/v2/skills 只查 DB skills 表；场景剧本是文件式（data/skills/scenarios/*/SKILL.md），
    无 DB 记录 -> 不展示。这里在启动时 upsert，status='published'。
    skill_code 带斜杠（"scenarios/<name>"），skill_storage._skill_path 会解析到现有目录，所有文件 API 免改。
    """
    from pathlib import Path
    from ..core.skill_storage import get_skill_storage
    from ..models.skill import Skill

    storage = get_skill_storage()
    scen_dir = Path(storage.root) / "scenarios"
    if not scen_dir.exists():
        return
    for md in scen_dir.glob("*/SKILL.md"):
        skill_code = f"scenarios/{md.parent.name}"
        meta = storage.parse_skill_md(skill_code)
        existing = db.query(Skill).filter(Skill.skill_code == skill_code).first()
        name = meta.get("name") or md.parent.name
        desc = meta.get("description")
        storage_path = str(storage._skill_path(skill_code))
        if existing:
            # 更新 name/description（用户可能编辑过 SKILL.md）
            existing.name = name
            if desc:
                existing.description = desc
            existing.storage_path = storage_path
            existing.status = "published"
        else:
            db.add(Skill(
                skill_code=skill_code,
                name=name,
                description=desc,
                skill_type=meta.get("skill_type") or "claude",
                status="published",
                storage_path=storage_path,
                app_type="chat",
                target_menu="chat",
            ))
    db.commit()


def init_db(db: Session):
    """数据库初始化（仅技能类型，不建概念/实体种子数据）。

    图谱只读主数据建模和业务活动建模维护的实体，不做内部初始化。
    """
    # 初始化默认技能类型
    from ..models.skill import SkillType
    if not db.query(SkillType).first():
        default_types = [
            SkillType(type_code="natural", name="自然语言", icon="ExperimentOutlined", color="#10b981", sort_order=1, ext="txt"),
            SkillType(type_code="python", name="Python", icon="CodeOutlined", color="#3b82f6", sort_order=2, ext="py"),
            SkillType(type_code="sql", name="SQL", icon="DatabaseOutlined", color="#f59e0b", sort_order=3, ext="sql"),
            SkillType(type_code="http", name="HTTP", icon="GlobalOutlined", color="#8b5cf6", sort_order=4, ext="yaml"),
            SkillType(type_code="mixed", name="混合", icon="ApiOutlined", color="#ec4899", sort_order=5, ext="yaml"),
        ]
        for t in default_types:
            db.add(t)
        db.commit()

    # 同步文件式场景剧本到 skills 表（技能管理页可见）
    _sync_scenario_skills(db)
