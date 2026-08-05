"""Plan-Execute 流程单元测试

覆盖关键纯函数（无外部依赖）：
  - TemplateResolver.resolve: 模板占位符解析
  - _match_l2_by_user_input: L2 模糊匹配（历史 Bug 回归保护）
  - _extract_where_clauses: WHERE 条件提取
  - _inject_user_input: 用户输入注入（replan 回归保护）
  - _tokenize_user_input: 分词
  - _match_cross_entity_fields: 跨实体字段升级
"""
import pytest

from app.services.plan_execute import (
    TemplateResolver,
    _match_l2_by_user_input,
    _extract_where_clauses,
    _inject_user_input,
    _tokenize_user_input,
    _expand_tokens_with_synonyms,
    _match_attributes,
    PlanStep,
    ExecutionPlan,
)


# --------------------------------------------------------------------------- #
# TemplateResolver
# --------------------------------------------------------------------------- #
class TestTemplateResolver:
    def setup_method(self):
        self.resolver = TemplateResolver()

    def test_简单字段解析(self):
        results = {1: {"name": "用电客户"}}
        assert self.resolver.resolve("{{step1.name}}", results) == "用电客户"

    def test_嵌套路径解析(self):
        results = {1: {"data": {"id": "123"}}}
        assert self.resolver.resolve("{{step1.data.id}}", results) == "123"

    def test_list转json(self):
        """list 必须用 json.dumps 输出双引号，否则嵌入 JSON 模板会失败"""
        results = {1: {"attrs": ["a", "b"]}}
        resolved = self.resolver.resolve("{{step1.attrs}}", results)
        assert resolved == '["a", "b"]', f"list 应转双引号 JSON: {resolved}"

    def test_dict转json(self):
        results = {1: {"conf": {"L2": "用电客户"}}}
        resolved = self.resolver.resolve("{{step1.conf}}", results)
        assert '"L2"' in resolved and "用电客户" in resolved

    def test_未找到步骤保留原占位符(self):
        """步骤不存在时保留 {{stepN.field}} 原文，不报错"""
        results = {1: {"name": "x"}}
        assert self.resolver.resolve("{{step2.name}}", results) == "{{step2.name}}"

    def test_字段为None保留原占位符(self):
        results = {1: {"name": None}}
        assert self.resolver.resolve("{{step1.name}}", results) == "{{step1.name}}"

    def test_无占位符原样返回(self):
        assert self.resolver.resolve("plain text", {}) == "plain text"

    def test_多个占位符同时解析(self):
        results = {1: {"a": "x"}, 2: {"b": "y"}}
        resolved = self.resolver.resolve("{{step1.a}}-{{step2.b}}", results)
        assert resolved == "x-y"

    def test_嵌套路径中间为None(self):
        results = {1: {"data": None}}
        assert self.resolver.resolve("{{step1.data.id}}", results) == "{{step1.data.id}}"

    def test_list内含dict转json(self):
        """list[dict] 也应正确转 JSON"""
        results = {1: {"items": [{"code": "a"}, {"code": "b"}]}}
        resolved = self.resolver.resolve("{{step1.items}}", results)
        assert '"code"' in resolved and "a" in resolved and "b" in resolved


# --------------------------------------------------------------------------- #
# _match_l2_by_user_input（历史 Bug 回归保护）
# --------------------------------------------------------------------------- #
class TestMatchL2ByUserInput:
    """验证 L2 模糊匹配逻辑

    背景：原实现直接选 sort_order 第一个 L2，导致"用电客户的名称..."
    被错误锁定为"项目定义"。修复后用字符串模糊匹配优先选"用电客户"。
    """

    def setup_method(self):
        self.all_l2 = [
            {"l2_name": "项目定义", "l2_id": "l2-proj"},
            {"l2_name": "用电客户", "l2_id": "l2-cust"},
            {"l2_name": "计量装置", "l2_id": "l2-meter"},
            {"l2_name": "客户", "l2_id": "l2-cust-short"},
        ]

    def test_完整包含匹配_用电客户(self):
        """'用电客户' 完整出现在用户问题中 → 匹配 l2-cust"""
        result = _match_l2_by_user_input("用电客户的名称、用能地址、联系电话", self.all_l2)
        assert result is not None
        assert result["l2_id"] == "l2-cust"

    def test_最长名称优先(self):
        """'用电客户'(4字) 比 '客户'(2字) 更具体，应优先匹配"""
        result = _match_l2_by_user_input("查用电客户的信息", self.all_l2)
        assert result["l2_id"] == "l2-cust"

    def test_计量装置匹配(self):
        result = _match_l2_by_user_input("查计量装置的电表号", self.all_l2)
        assert result["l2_id"] == "l2-meter"

    def test_无匹配返回None(self):
        result = _match_l2_by_user_input("查天气情况", self.all_l2)
        assert result is None

    def test_空输入返回None(self):
        assert _match_l2_by_user_input("", self.all_l2) is None

    def test_空l2列表返回None(self):
        assert _match_l2_by_user_input("用电客户", []) is None

    def test_纯空格返回None(self):
        assert _match_l2_by_user_input("   ", self.all_l2) is None

    def test_反向包含匹配(self):
        """用户问题分词后关键词出现在 L2 名称中"""
        result = _match_l2_by_user_input("项目", self.all_l2)
        assert result is not None
        assert result["l2_id"] == "l2-proj"

    def test_不误锁项目定义(self):
        """回归测试：'用电客户的名称' 不应锁成 '项目定义'"""
        result = _match_l2_by_user_input("帮查询用电客户的名称、用能地址、联系电话、证件类型、证件号码等信息", self.all_l2)
        assert result is not None
        assert result["l2_id"] == "l2-cust", f"不应锁成项目定义，实际: {result}"


# --------------------------------------------------------------------------- #
# _extract_where_clauses（WHERE 条件提取）
# --------------------------------------------------------------------------- #
class TestExtractWhereClauses:
    def setup_method(self):
        self.attrs = [
            {"attribute_name": "客户名称", "attribute_code": "cust_name"},
            {"attribute_name": "客户编号", "attribute_code": "cust_id"},
            {"attribute_name": "创建时间", "attribute_code": "create_time"},
        ]

    def test_姓名约束(self):
        clauses = _extract_where_clauses("叫张三的客户", self.attrs)
        assert any("cust_name LIKE" in c and "张三" in c for c in clauses), f"应生成 LIKE: {clauses}"

    def test_姓名约束_名为前缀(self):
        clauses = _extract_where_clauses("名为李四", self.attrs)
        assert any("cust_name LIKE" in c for c in clauses), f"应为名称列: {clauses}"

    def test_户号约束(self):
        clauses = _extract_where_clauses("户号12345", self.attrs)
        assert any("cust_id = 12345" in c for c in clauses), f"应生成等值: {clauses}"

    def test_年份约束_暂不绑定列(self):
        """年份约束当前实现跳过（不绑定具体列），返回空"""
        clauses = _extract_where_clauses("2024年的数据", self.attrs)
        # 当前实现：YEAR 模板不绑定列，pass 跳过
        assert clauses == [], f"年份当前不绑定列，应返回空: {clauses}"

    def test_无值约束返回空(self):
        clauses = _extract_where_clauses("查所有客户", self.attrs)
        assert clauses == []

    def test_空输入返回空(self):
        assert _extract_where_clauses("", self.attrs) == []

    def test_无名称列不生成like(self):
        """attrs 里没有名称类字段时，LIKE 不生成"""
        attrs_no_name = [{"attribute_name": "客户编号", "attribute_code": "cust_id"}]
        clauses = _extract_where_clauses("叫张三", attrs_no_name)
        assert clauses == [], f"无名称列不应生成 LIKE: {clauses}"

    def test_无id列不生成等值(self):
        """attrs 里没有编号类字段时，等值不生成"""
        attrs_no_id = [{"attribute_name": "客户名称", "attribute_code": "cust_name"}]
        clauses = _extract_where_clauses("户号12345", attrs_no_id)
        assert clauses == [], f"无 id 列不应生成等值: {clauses}"


# --------------------------------------------------------------------------- #
# _inject_user_input（replan 回归保护）
# --------------------------------------------------------------------------- #
class TestInjectUserInput:
    """验证用户输入注入到计划模板

    背景：replan 生成的计划模板含 {{step0.user_input}} 占位符，
    若不注入执行时会触发"参数模板未解析"导致重试失败。
    """

    def test_替换user_input占位符(self):
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[
                PlanStep(step_id=1, action="fetch_l1_l2_tree",
                         params_template='{"user_input":"{{step0.user_input}}"}'),
            ],
        )
        injected = _inject_user_input(plan, "查用电客户")
        assert "{{step0.user_input}}" not in injected.steps[0].params_template
        assert "查用电客户" in injected.steps[0].params_template

    def test_替换keyword占位符(self):
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[
                PlanStep(step_id=1, action="search",
                         params_template='{"keyword":"{{step0.keyword}}"}'),
            ],
        )
        injected = _inject_user_input(plan, "用电客户")
        assert "{{step0.keyword}}" not in injected.steps[0].params_template
        assert "用电客户" in injected.steps[0].params_template

    def test_转义双引号(self):
        """用户输入含双引号时应转义，避免破坏 JSON 结构"""
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[
                PlanStep(step_id=1, action="fetch",
                         params_template='{"q":"{{step0.user_input}}"}'),
            ],
        )
        injected = _inject_user_input(plan, '查"特殊"字符')
        # 转义后应为 \"
        assert '\\"特殊\\"' in injected.steps[0].params_template

    def test_转义反斜杠(self):
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[
                PlanStep(step_id=1, action="fetch",
                         params_template='{"q":"{{step0.user_input}}"}'),
            ],
        )
        injected = _inject_user_input(plan, "C:\\Users\\test")
        assert "\\\\Users\\\\" in injected.steps[0].params_template or "\\\\Users" in injected.steps[0].params_template

    def test_无占位符不影响(self):
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[
                PlanStep(step_id=1, action="execute",
                         params_template='{"sql":"SELECT 1"}'),
            ],
        )
        injected = _inject_user_input(plan, "查用电客户")
        assert injected.steps[0].params_template == '{"sql":"SELECT 1"}'

    def test_不修改原计划(self):
        """_inject_user_input 应 deepcopy，不修改原 plan"""
        original_template = '{"q":"{{step0.user_input}}"}'
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[PlanStep(step_id=1, action="fetch", params_template=original_template)],
        )
        _inject_user_input(plan, "查用电客户")
        assert plan.steps[0].params_template == original_template, "原计划不应被修改"

    def test_截断超长输入(self):
        """超过 100 字符的输入应截断"""
        long_input = "查" * 200
        plan = ExecutionPlan(
            skill_type="basic-query",
            steps=[PlanStep(step_id=1, action="fetch", params_template='{"q":"{{step0.user_input}}"}')],
        )
        injected = _inject_user_input(plan, long_input)
        # 截断到 100 字符
        assert "查" * 100 in injected.steps[0].params_template
        assert "查" * 101 not in injected.steps[0].params_template


# --------------------------------------------------------------------------- #
# _tokenize_user_input（分词）
# --------------------------------------------------------------------------- #
class TestTokenizeUserInput:
    def test_标点切分(self):
        tokens = _tokenize_user_input("用电客户、用能地址、联系电话")
        assert "用电客户" in tokens
        assert "用能地址" in tokens

    def test_去停用词(self):
        tokens = _tokenize_user_input("帮我查询一下用电客户的信息")
        # "帮我" "查询" "一下" "信息" 是停用词
        assert "用电客户" in tokens

    def test_空输入返回空(self):
        assert _tokenize_user_input("") == []

    def test_纯停用词返回空(self):
        tokens = _tokenize_user_input("的了的了")
        assert tokens == []

    def test_保留长度大于等于2的token(self):
        tokens = _tokenize_user_input("a、ab、abc")
        # "a" 长度1被过滤，"ab" "abc" 保留
        assert "ab" in tokens
        assert "abc" in tokens


# --------------------------------------------------------------------------- #
# _expand_tokens_with_synonyms（同义词扩展）
# --------------------------------------------------------------------------- #
class TestExpandTokensWithSynonyms:
    def test_户名扩展为客户名称(self):
        """'户名' 应扩展出 '客户名称' 等同义词"""
        expanded = _expand_tokens_with_synonyms(["户名"])
        assert "户名" in expanded
        # 至少扩展出一个同义词
        assert len(expanded) > 1, f"户名应扩展出同义词: {expanded}"

    def test_无匹配返回原token(self):
        expanded = _expand_tokens_with_synonyms(["不存在的词xyz"])
        assert expanded == ["不存在的词xyz"]

    def test_空列表返回空(self):
        assert _expand_tokens_with_synonyms([]) == []

    def test_去重保序(self):
        expanded = _expand_tokens_with_synonyms(["户名", "户名"])
        # 去重
        assert expanded.count("户名") == 1


# --------------------------------------------------------------------------- #
# _match_attributes（属性匹配）
# --------------------------------------------------------------------------- #
class TestMatchAttributes:
    def test_双向子串匹配(self):
        attrs = [
            {"attribute_name": "客户名称", "attribute_code": "cust_name"},
            {"attribute_name": "联系电话", "attribute_code": "phone"},
        ]
        # "名称" in "客户名称"
        matched = _match_attributes(["名称", "联系电话"], attrs)
        codes = [c for c, _ in matched]
        assert "cust_name" in codes
        assert "phone" in codes

    def test_无匹配返回空(self):
        attrs = [{"attribute_name": "客户名称", "attribute_code": "cust_name"}]
        matched = _match_attributes(["不存在的字段"], attrs)
        assert matched == []

    def test_跳过非dict属性(self):
        attrs = [{"attribute_name": "客户名称", "attribute_code": "cust_name"}, "invalid"]
        matched = _match_attributes(["名称"], attrs)
        assert len(matched) == 1

    def test_跳过空属性名(self):
        attrs = [{"attribute_name": "", "attribute_code": "x"}, {"attribute_name": "名称", "attribute_code": "y"}]
        matched = _match_attributes(["名称"], attrs)
        assert len(matched) == 1
        assert matched[0][0] == "y"
