import pytest

from app.services.skill_router import (
    classify_intent,
    get_skill_category,
    needs_sql,
    SKILL_CATEGORIES,
)


class TestBasicQuery:
    def test_基础查询_简单问句(self):
        assert classify_intent("张三的户名是什么情况") == "basic-query"

    def test_基础查询_无关键词兜底(self):
        assert classify_intent("帮我看看这个数据") == "basic-query"

    def test_基础查询_普通描述(self):
        assert classify_intent("昨天发生了什么事") == "basic-query"


class TestAggregateQuery:
    def test_聚合查询_数量(self):
        assert classify_intent("一共有多少个客户") == "aggregate-query"

    def test_聚合查询_统计(self):
        assert classify_intent("按区域统计用户数") == "aggregate-query"

    def test_聚合查询_平均(self):
        assert classify_intent("平均电费是多少") == "aggregate-query"

    def test_聚合查询_占比(self):
        assert classify_intent("各类用户占比情况") == "aggregate-query"


class TestTopnQuery:
    def test_排名查询_最大(self):
        assert classify_intent("用电量最大的客户") == "topn-query"

    def test_排名查询_前N(self):
        assert classify_intent("排名前10的变压器") == "topn-query"

    def test_排名查询_排序(self):
        assert classify_intent("按电费从高到低排序") == "topn-query"


class TestDirectQuery:
    def test_直查_维度表(self):
        assert classify_intent("dim_customer 表里有什么") == "direct-query"

    def test_直查_明细表(self):
        assert classify_intent("查一下 dwd_power_usage 的数据") == "direct-query"

    def test_直查_汇总表(self):
        assert classify_intent("查一下 dws_monthly_bill 的数据") == "direct-query"


class TestMultiHopQuery:
    def test_多跳_关联(self):
        assert classify_intent("客户关联的电表信息") == "multi-hop-query"

    def test_多跳_穿透(self):
        assert classify_intent("穿透查询客户和变压器") == "multi-hop-query"

    def test_多跳_join(self):
        assert classify_intent("join 客户表和电表表") == "multi-hop-query"


class TestExplainConcept:
    def test_概念解释_什么是(self):
        assert classify_intent("什么是基本电费") == "explain-concept"

    def test_概念解释_是什么意思(self):
        assert classify_intent("功率因数是什么意思") == "explain-concept"

    def test_概念解释_区别(self):
        assert classify_intent("峰谷电价和阶梯电价的区别") == "explain-concept"

    def test_概念解释_定义(self):
        assert classify_intent("需量的定义") == "explain-concept"


class TestExploreGraph:
    def test_图探索_有哪些(self):
        assert classify_intent("客户实体有哪些属性") == "explore-graph"

    def test_图探索_包含什么(self):
        assert classify_intent("这个业务域包含什么") == "explore-graph"

    def test_图探索_层级(self):
        assert classify_intent("看一下数据的层级结构") == "explore-graph"


class TestFindEntity:
    def test_找实体_在哪个表(self):
        assert classify_intent("户号这个字段在哪个表") == "find-entity"

    def test_找实体_数据字典(self):
        assert classify_intent("查看数据字典") == "find-entity"

    def test_找实体_找字段(self):
        assert classify_intent("帮我找一下客户编号字段") == "find-entity"


class TestDataQuality:
    def test_数据质量_空值(self):
        assert classify_intent("这个表有多少空值") == "data-quality"

    def test_数据质量_重复(self):
        assert classify_intent("检查数据有没有重复") == "data-quality"

    def test_数据质量_完整率(self):
        assert classify_intent("客户表的完整率是多少") == "data-quality"


class TestTraceLineage:
    def test_血缘_来源(self):
        assert classify_intent("这个指标的数据来源是什么") == "trace-lineage"

    def test_血缘_上游(self):
        assert classify_intent("这张表的上游是哪张") == "trace-lineage"

    def test_血缘_怎么来的(self):
        assert classify_intent("这个汇总数据是怎么来的") == "trace-lineage"


class TestExecuteSql:
    def test_续轮_执行(self):
        assert classify_intent("执行") == "execute-sql"

    def test_续轮_确认(self):
        assert classify_intent("确认") == "execute-sql"

    def test_续轮_ok(self):
        assert classify_intent("ok") == "execute-sql"

    def test_续轮_yes(self):
        assert classify_intent("yes") == "execute-sql"

    def test_续轮_好的(self):
        assert classify_intent("好的") == "execute-sql"

    def test_续轮_是(self):
        assert classify_intent("是") == "execute-sql"


class TestBoundary:
    def test_空字符串(self):
        assert classify_intent("") == "basic-query"

    def test_纯空格(self):
        assert classify_intent("   ") == "basic-query"

    def test_纯数字(self):
        assert classify_intent("12345") == "basic-query"

    def test_超长文本(self):
        long_text = "请帮我查询一下数据" * 200
        result = classify_intent(long_text)
        assert isinstance(result, str)
        assert result in list(SKILL_CATEGORIES.keys()) + ["execute-sql"]

    def test_特殊字符(self):
        assert classify_intent("!@#$%^&*()") == "basic-query"


class TestPriority:
    def test_什么是数量_应匹配概念而非聚合(self):
        assert classify_intent("什么是变压器的数量") == "explain-concept"

    def test_是什么意思_优先于聚合(self):
        assert classify_intent("平均电费是什么意思") == "explain-concept"

    def test_数据质量优先于聚合(self):
        assert classify_intent("有多少个空值") == "data-quality"

    def test_血缘优先于其他(self):
        assert classify_intent("数据来源是什么") == "trace-lineage"


class TestNeedsSql:
    def test_问数类需要sql(self):
        for skill in ["basic-query", "aggregate-query", "topn-query", "direct-query", "multi-hop-query"]:
            assert needs_sql(skill) is True

    def test_知识类不需要sql(self):
        for skill in ["explain-concept", "explore-graph", "find-entity", "data-quality", "trace-lineage"]:
            assert needs_sql(skill) is False

    def test_未知技能默认需要sql(self):
        assert needs_sql("unknown-skill") is True


class TestGetSkillCategory:
    def test_问数类分类(self):
        assert get_skill_category("basic-query") == "问数"
        assert get_skill_category("aggregate-query") == "问数"

    def test_知识类分类(self):
        assert get_skill_category("explain-concept") == "知识"
        assert get_skill_category("trace-lineage") == "知识"

    def test_未知技能默认问数(self):
        assert get_skill_category("not-exist") == "问数"


# --------------------------------------------------------------------------- #
# 跨实体字段升级 multi-hop（历史 Bug 回归保护）
# --------------------------------------------------------------------------- #
class TestCrossEntityFieldsUpgrade:
    """验证 _match_cross_entity_fields 隐式升级逻辑

    背景：用户问"用电客户的名称、联系电话、证件号码"时，字段分散在主表+副表，
    但不含 multi-hop 关键词（关联/穿透/join），原逻辑误判为 basic-query 导致
    只查主表丢失副表字段。修复后通过字段组合检测升级为 multi-hop-query。
    """

    def test_主表字段加副表字段升级_multi_hop(self):
        """主表字段（名称）+ 副表字段（联系电话）→ multi-hop"""
        assert classify_intent("用电客户的名称、联系电话、证件号码") == "multi-hop-query"

    def test_主表字段加单副表字段升级(self):
        """主表字段（户号）+ 一个副表类别（电费）→ multi-hop"""
        assert classify_intent("查用电客户的户号和电费") == "multi-hop-query"

    def test_多个副表字段类别升级(self):
        """两个不同副表类别（联系人+证件）→ multi-hop（无需主表字段）"""
        assert classify_intent("联系电话和证件号码") == "multi-hop-query"

    def test_单一副表字段不升级(self):
        """只有联系电话（单一副表字段）→ basic-query，不应升级"""
        # 注意：联系电话单独出现时不应触发 multi-hop，避免过度升级
        result = classify_intent("查所有联系电话")
        assert result == "basic-query", f"单一副表字段不应升级为 multi-hop，实际: {result}"

    def test_仅主表字段不升级(self):
        """只有名称（主表字段）→ basic-query"""
        assert classify_intent("查用电客户的名称") == "basic-query"

    def test_电费和计量升级(self):
        """电费+计量两个副表类别 → multi-hop"""
        assert classify_intent("查电费和电表号") == "multi-hop-query"

    def test_用能地址加证件号码升级(self):
        """用能地址+证件号码（两个副表类别）→ multi-hop"""
        assert classify_intent("查用能地址和身份证号") == "multi-hop-query"

    def test_合同编号加联系电话升级(self):
        """合同编号+联系电话（两个副表类别）→ multi-hop"""
        assert classify_intent("查合同编号和手机号") == "multi-hop-query"


# --------------------------------------------------------------------------- #
# 优先级冲突与复合问句（边界场景）
# --------------------------------------------------------------------------- #
class TestPriorityConflicts:
    def test_什么是数据来源_应匹配血缘而非概念(self):
        """trace-lineage 优先级(1) > explain-concept 优先级(3)"""
        assert classify_intent("什么是数据来源") == "trace-lineage"

    def test_平均电费是什么意思_应匹配概念而非聚合(self):
        """explain-concept 优先级(3) > aggregate-query 优先级(9)"""
        assert classify_intent("平均电费是什么意思") == "explain-concept"

    def test_有多少个空值_应匹配质量而非聚合(self):
        """data-quality 优先级(2) > aggregate-query 优先级(9)"""
        assert classify_intent("有多少个空值") == "data-quality"


class TestCompoundQueries:
    def test_表名加多跳关键词(self):
        """含 dim_ 表名 + multi-hop 关键词 → direct-query（优先级6 > 优先级7）"""
        # direct-query 优先级高于 multi-hop
        assert classify_intent("查 dim_customer 关联的用电客户") == "direct-query"

    def test_大小写混合_join(self):
        """JOIN 大写 → multi-hop（已 lower() 处理）"""
        assert classify_intent("JOIN 用电客户和电表") == "multi-hop-query"

    def test_大小写混合_top(self):
        """TOP 10 大写 → topn-query"""
        assert classify_intent("TOP 10 用电客户") == "topn-query"

    def test_大小写混合_sum(self):
        """SUM 大写 → aggregate-query"""
        assert classify_intent("SUM 用电量") == "aggregate-query"


# --------------------------------------------------------------------------- #
# 续轮场景 has_context 参数
# --------------------------------------------------------------------------- #
class TestContinuationContext:
    def test_续轮_执行_has_context(self):
        """has_context=True 时 '执行' → execute-sql"""
        assert classify_intent("执行", has_context=True) == "execute-sql"

    def test_续轮_确认_has_context(self):
        assert classify_intent("确认", has_context=True) == "execute-sql"

    def test_续轮_ok_has_context(self):
        assert classify_intent("ok", has_context=True) == "execute-sql"

    def test_无上下文_执行也匹配续轮(self):
        """无上下文时 '执行' 仍匹配 execute-sql（_CONTINUATION_KEYWORDS 精确匹配）"""
        # 注意：当前实现不论 has_context 都会匹配 _CONTINUATION_KEYWORDS
        assert classify_intent("执行", has_context=False) == "execute-sql"
