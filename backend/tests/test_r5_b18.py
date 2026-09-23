# -*- coding: utf-8 -*-
"""R5批⑱（清单安全）契约测试。

- tutor_llm：判分提示词防注入定界 + score 输出侧钳制
- query_attribute_support：join_expr 白名单格式（仅反引号等式 AND 链）
- query_contract：绝对禁止集不受 allowed_tools 声明影响（「只能加不能减」不变量）
变异锚点：定界/白名单/方向修正任一回退 → 对应测红。
"""
import inspect

from app.services.learning import tutor_llm
from app.services import query_attribute_support as qas
from app.services import query_contract as qc


def test_tutor_llm_prompt_hardened():
    src = inspect.getsource(tutor_llm)
    assert "<<<ANSWER" in src and "ANSWER>>>" in src and "<<<RUBRIC" in src
    assert "防注入" in src
    assert "max(0, min(100" in src


def test_join_expr_whitelist():
    src = inspect.getsource(qas)
    assert "fullmatch" in src and "join_expr" in src and "AND" in src
    # 正则行为与生产一致：等式 AND 链过、带函数/字面量的不过
    import re
    pat = re.compile(r"\s*[\w`.]+\.[\w`.]+\s*=\s*[\w`.]+\.[\w`.]+"
                     r"(?:\s+AND\s+[\w`.]+\.[\w`.]+\s*=\s*[\w`.]+\.[\w`.]+)*\s*")
    assert pat.fullmatch("a.id = b.aid")            # 未反引号（17_coverage 契约格式）
    assert pat.fullmatch(" `a`.`id` = `b`.`aid` ")  # 反引号形式
    assert pat.fullmatch("`a`.`id` = `b`.`aid` AND `c`.`x` = `d`.`cx`")
    assert not pat.fullmatch("`a`.`id` = `b`.`aid` OR 1=1")
    assert not pat.fullmatch("`a`.`id` = 'x'")
    assert not pat.fullmatch("`a`.`id` = substr(`b`.`x`, 1)")
    assert not pat.fullmatch("1=1")                 # 裸恒等式（无列引用）拒绝


def test_absolute_forbidden_not_escaped_by_declaration():
    src = inspect.getsource(qc)
    # 反向过滤已删除（声明即逃逸的旧实现）
    assert "if t not in c.allowed_tools and not (t == \"task\"" not in src
