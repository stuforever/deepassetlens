"""共享测试助手：解析 distribution-overload 户变关系模板（scenario_strict 合规 SQL）。

评审 P0-2 后，distribution-overload 声明 template_mode: scenario_strict ——
结构指纹与模板不一致（同表但骨架不同）即拒绝。因此"合法执行"类断言必须使用
真实模板（或仅字面量/声明式【动态】扩展的变体），不能再拿自定义简化 SQL 当合法。
"""
from pathlib import Path

from app.services.skill_catalog import get_catalog
from app.services.template_guard import load_template, resolve_entity_aliases, _resolve_entity_refs


def relationship_template_sql() -> str:
    """返回已解析（⟦别名⟧ -> 物理表名）的户变关系模板全文。"""
    skill = get_catalog().load_skill("distribution-overload")
    raw = load_template(Path(skill.path.parent) / "templates/step1_household_transformer.sql")
    return _resolve_entity_refs(resolve_entity_aliases(raw, skill.entity_aliases))
