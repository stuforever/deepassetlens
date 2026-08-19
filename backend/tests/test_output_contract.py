"""输出契约校验脚本测试（单表改造配套，distribution-overload/scripts）。

验证 scripts/validate_output_contract.py 的 validate() 逻辑：
- 发现 GFM 明细表 -> 报错
- 无证据全量结论（"全部台区均为单路"/"全部正常"）-> 报错
- "样本显示/样本内"限定 -> 通过
- SQL 显式聚合统计证据（COUNT/GROUP BY/聚合/统计）-> 通过
- row_count 全量结论（"共 N 条"）-> 通过（合法）
- 标准答案示例文件 -> 通过

运行方式：
    cd backend && python -m pytest tests/test_output_contract.py -v
"""
import importlib.util
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "data" / "skills" / "scenarios" / "distribution-overload" / "scripts" / "validate_output_contract.py"
)
_SPEC = importlib.util.spec_from_file_location("validate_output_contract", _SCRIPT)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
validate = _MOD.validate


class TestOutputContractValidator:
    def test_发现GFM明细表报错(self):
        text = "结论。\n\n| 客户类型 | 客户编号 |\n|---|---|\n| 用电户 | 101 |\n"
        problems = validate(text)
        assert any("GFM" in p for p in problems), problems

    def test_无证据全量结论报错(self):
        text = "全部台区均为单路供电，客户状态全部正常。"
        problems = validate(text)
        assert problems, "应报无证据全量结论"
        # 单行内子串去重：只报最长匹配（"全部台区均为单路"）
        assert sum("单路" in p for p in problems) == 1, problems
        assert any("正常" in p for p in problems), problems

    def test_样本显示限定通过(self):
        text = "样本显示台区均为单路供电，样本内客户状态正常。共 101 条。"
        assert validate(text) == [], validate(text)

    def test_聚合统计证据通过(self):
        text = "经 SQL 聚合统计（COUNT/GROUP BY）：全部 101 个计量点用途均为用电。"
        assert validate(text) == [], validate(text)

    def test_row_count全量结论通过(self):
        # "全部户变关系"是名词短语（全部关系），"共 101 条"是 row_count 合法全量结论
        text = "已获取全部户变关系，共 101 条记录，完整明细见下方查询结果表。"
        assert validate(text) == [], validate(text)

    def test_标准答案示例通过(self):
        example = _SCRIPT.parent.parent / "examples" / "household-transformer-output.md"
        assert example.exists(), "示例文件应存在"
        assert validate(example.read_text(encoding="utf-8")) == []


# ============================================================================
# 以下为受控 Skill 问答平台 v2 新增：app/services/output_contract.py（后端运行时
# 最终输出校验：完整数据推前端后禁止再输出 Markdown 明细表）
# ============================================================================
from app.services.output_contract import (  # noqa: E402
    count_markdown_tables,
    scrub_markdown_tables,
    validate_final_output,
)


class TestBackendMarkdownTableDetection:
    def test_no_table(self):
        assert count_markdown_tables("共 101 条，完整明细见下方查询结果表。") == 0

    def test_single_table_rows(self):
        text = "| a | b |\n|---|---|\n| 1 | 2 |"
        assert count_markdown_tables(text) == 3


class TestBackendValidate:
    def test_ui_result_no_table_ok(self):
        chk = validate_final_output("共101条，见下方查询结果表。", result_available_for_ui=True)
        assert chk.ok is True

    def test_ui_result_with_table_rejected(self):
        chk = validate_final_output("| 客户 | 台区 |\n| 001 | A |", result_available_for_ui=True)
        assert chk.ok is False
        assert chk.detail_tables_found > 0

    def test_no_ui_result_table_allowed(self):
        chk = validate_final_output("| 概念 | 定义 |\n| 台区 | 计算单元 |", result_available_for_ui=False)
        assert chk.ok is True


class TestBackendScrub:
    def test_scrub_removes_tables(self):
        text = "结论\n| a | b |\n| 1 | 2 |\n建议：详见明细"
        out = scrub_markdown_tables(text)
        assert "结论" in out
        assert "| a | b |" not in out

    def test_scrub_marks_reference(self):
        text = "| a | b |\n| 1 | 2 |\n后文"
        out = scrub_markdown_tables(text)
        assert "查询结果表" in out

    def test_scrub_noop_without_table(self):
        text = "没有表格的结论"
        assert scrub_markdown_tables(text) == text
