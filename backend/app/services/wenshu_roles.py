# -*- coding: utf-8 -*-
"""B2（v4§三/§四）：问数角色卡预置注册表 + role_id 注入。

角色与技能正交：角色改「怎么说」，技能改「干什么」。角色卡=基座 system_prompt 之上的
风格段（拼接、不替换）——工作流契约/四段式/取数铁律全部保留在基座，角色只调语气与呈现。

- 预置=代码常量（非 DB）：3 张卡照 v4§四 文案；批⑤ 设置「角色卡」页对 wenshu 开放编辑时
  再议存储迁移，本批只定契约（role_id 三个稳定键即对外契约）。
- `默认分析师` style_prompt=None：apply_role 原样返回卡=现状等价（逐字节）。
- 仅 wenshu 预置；其他专家 ValueError（角色下拉其他专家暂空，不误挂问数语气）。
"""
from typing import Any, Dict, Optional

WENSHU_ROLE_CARDS = [
    {
        "role_id": "analyst_default",
        "name": "默认分析师",
        "description": "现状等价：口径严谨、四段式",
        "style_prompt": None,
    },
    {
        "role_id": "business_plain",
        "name": "业务白话型",
        "description": "少术语、多举例、结论先行",
        "style_prompt": (
            "## 回答风格：业务白话型\n"
            "- 结论先行：第一句话就给答案，依据放后面。\n"
            "- 少用术语：必须用专业词时，紧跟一句话通俗解释。\n"
            "- 多举例：关键结论配一个贴近业务的例子或类比。\n"
            "- 语言平实：面向业务人员可读；SQL/图查询细节不进正文（放折叠/附注）。"
        ),
    },
    {
        "role_id": "tech_detail",
        "name": "技术 detail 型",
        "description": "附 SQL/口径/血缘细节",
        "style_prompt": (
            "## 回答风格：技术 detail 型\n"
            "- 附取数 SQL（或图查询语句）与关键过滤条件。\n"
            "- 每个数字注明口径：统计范围、时间窗、去重规则。\n"
            "- 给出字段/实体血缘脉络：数据从哪来、经过哪些加工。\n"
            "- 结构化呈现：结论 → 口径 → SQL/查询 → 血缘 → 注意事项。"
        ),
    },
]


def apply_role(expert_id: str, role_id: Optional[str], card: Dict[str, Any]) -> Dict[str, Any]:
    """角色注入（B2）：role_id 空 → 卡原样返回（现状等价，逐字节不变）。

    角色卡=基座+风格段拼接（不替换基座、不拆工作流契约）；默认分析师无风格段=现状等价。
    未知角色 / 非 wenshu 专家 → ValueError（调用方定口径：请求链转 422，构建链告警回退基座）。
    纯函数：不改入参卡。
    """
    if not role_id:
        return card
    if (expert_id or "wenshu") != "wenshu":
        raise ValueError(f"角色卡仅问数（wenshu）可用，收到 expert={expert_id}")
    role = next((c for c in WENSHU_ROLE_CARDS if c["role_id"] == role_id), None)
    if role is None:
        raise ValueError(f"未知角色卡: {role_id}")
    style = role.get("style_prompt")
    if not style:
        return card
    base = card.get("system_prompt") or ""
    merged = (base + "\n\n" + style) if base else style
    return {**card, "system_prompt": merged}
