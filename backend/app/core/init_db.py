from sqlalchemy.orm import Session


# 安全控制中心基线策略（《安全控制中心实施设计》2.1 种子数据）
# 六条：五类对外（capability/sql_safety/template/engine_lock/output）+ 审批轨（approval_track）
GUARD_POLICY_SEED = [
    {
        "guard_id": "capability",
        "title": "能力控制",
        "risk_level": "red",
        "params": {"forbidden_tools": ["task", "write_file", "edit_file", "execute", "grep", "glob"],
                   "absolute_tools": ["execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api"]},
        "description": {
            "what": "限制模型可调用的工具集合：全局硬禁危险工具（task 子代理/写文件/Shell 执行），仅放行受控数据工具与只读检索工具。",
            "lose": "关闭后模型可调用 task 子代理、写文件、执行 Shell 等高风险工具，具备逃逸能力。",
            "remain": "SQL 执行仍受 SQL 安全控制与模板控制保护，但工具面显著扩大。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "sql_safety",
        "title": "SQL 安全控制",
        "risk_level": "red",
        "params": {"limit_max": 500, "func_blacklist": ["sleep", "benchmark", "load_file", "pg_sleep", "into_outfile"]},
        "description": {
            "what": "对 SQL 型工具做 AST 级安全校验：只读语句（SELECT/WITH）、禁副作用函数、表白名单、强制 LIMIT。",
            "lose": "关闭后 DDL/DML/危险函数/超大结果集将直接放行，存在数据损坏与注入风险。",
            "remain": "模板控制仍拦截越表 SQL，但非模板路径的 SQL 将失去机械安全校验。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "template",
        "title": "模板控制",
        "risk_level": "yellow",
        "params": {"strict": True},
        "description": {
            "what": "受控场景下 SQL 必须来自已批准模板（表集合 ⊆ 模板、SELECT-only、无 UNION 绕过），结构指纹与模板一致才放行。",
            "lose": "关闭后模型可自由拼装 SQL 结构，表集合校验失效，数据语义可能跑偏。",
            "remain": "SQL 安全控制仍拦截非只读语句，但模板约束消失。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "engine_lock",
        "title": "引擎控制",
        "risk_level": "yellow",
        "params": {"lock_engine": True},
        "description": {
            "what": "数据工具必须匹配已确认的数据引擎（单引擎锁定 / 多引擎逐源确认），引擎由平台锁定不由模型拍板。",
            "lose": "关闭后模型可跨引擎混查，结果可能来自错误数据源且无一致性保障。",
            "remain": "数据源模式守卫仍拦截 execute_sql 对非 physical_table 的误用。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "output",
        "title": "输出控制",
        "risk_level": "yellow",
        "params": {"forbid_markdown_detail_table": True},
        "description": {
            "what": "控制最终答案输出形态：禁止与结果表同字段的 Markdown 明细表，强制结论/发现/建议分层输出。",
            "lose": "关闭后模型可输出冗余明细表，前端展示被遮挡，回答结构退化。",
            "remain": "查询结果表仍由前端权威渲染，不影响数据本身。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "approval_track",
        "title": "审批轨",
        "risk_level": "green",
        "params": {"interrupt_on": ["step2_power_aggregation", "step3_load_ratio"]},
        "description": {
            "what": "高风险步骤（功率汇集/负载倒排）执行前装配审批中断点，拦截时进入人工审批队列。",
            "lose": "关闭后高风险步骤直接自动执行，跳过人工审批环节。",
            "remain": "拦截记录仍留痕，只是不再阻塞等待审批。",
        },
        "confirm_required": False,
    },
]


def _seed_guard_policies(db: Session):
    """安全控制中心基线策略种子：仅当表为空时插入（幂等）。"""
    from ..models.base import GuardPolicy
    if db.query(GuardPolicy).first():
        return
    for p in GUARD_POLICY_SEED:
        db.add(GuardPolicy(
            guard_id=p["guard_id"], title=p["title"], enabled=True, mode="block",
            params=p.get("params"), risk_level=p["risk_level"],
            description=p.get("description"), confirm_required=p.get("confirm_required", True),
            version=1,
        ))
    db.commit()


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

    # 安全控制中心基线策略（幂等：仅表空时插入）
    _seed_guard_policies(db)
