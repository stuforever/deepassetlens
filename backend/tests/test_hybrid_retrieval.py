import pytest

from app.services.hybrid_retrieval import tokenize_query


class TestDomainTokenize:
    def test_电力术语分词_用电客户和户号(self, sample_domain_query):
        tokens = tokenize_query(sample_domain_query)
        assert "用电客户" in tokens
        assert "户号" in tokens

    def test_电力术语分词_变压器(self):
        tokens = tokenize_query("变压器的容量")
        assert "变压器" in tokens

    def test_电力术语分词_电费电价(self):
        tokens = tokenize_query("电费和电价")
        assert "电费" in tokens
        assert "电价" in tokens

    def test_电力术语分词_计量点(self):
        tokens = tokenize_query("计量点编号")
        assert "计量点" in tokens


class TestStopWords:
    def test_停用词过滤_请帮我查一下(self):
        tokens = tokenize_query("请帮我查一下")
        assert "请" not in tokens
        assert "帮" not in tokens
        assert "我" not in tokens
        assert "一下" not in tokens

    def test_停用词过滤_的了在是(self):
        tokens = tokenize_query("的 了 在 是")
        assert len(tokens) == 0

    def test_停用词不影响领域词(self):
        tokens = tokenize_query("请查一下户号")
        assert "户号" in tokens
        assert "请" not in tokens


class TestEmptyInput:
    def test_空字符串返回空列表(self):
        assert tokenize_query("") == []

    def test_none返回空列表(self):
        assert tokenize_query(None) == []

    def test_纯空格返回空列表(self):
        assert tokenize_query("   ") == []


class TestDedup:
    def test_重复词去重(self):
        tokens = tokenize_query("户号户号")
        assert tokens.count("户号") == 1

    def test_多次出现只保留一次(self):
        tokens = tokenize_query("电费 电费 电费")
        assert tokens.count("电费") == 1

    def test_不同词不去重(self):
        tokens = tokenize_query("电费 电价")
        assert "电费" in tokens
        assert "电价" in tokens


class TestReturnType:
    def test_返回列表类型(self):
        result = tokenize_query("变压器")
        assert isinstance(result, list)

    def test_元素为字符串(self):
        result = tokenize_query("用电客户")
        for item in result:
            assert isinstance(item, str)
