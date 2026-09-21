"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
# T9 匹配引擎测试 — 简报字面用例 + pypinyin 降级钉住
import sys

from app.services.sishu_full.learning.recitation.matcher import check_segment


def test_correct_and_homophone_and_wrong():
    ref = "大青树下的小学"                      # 归一化总字数 7
    r1 = check_segment(ref, "大青树下的小学")    # 全对
    assert r1["score"] == 1.0 and not r1["wrong_chars"] and not r1["homophones"]
    r2 = check_segment(ref, "大青树下的雪")      # "学"→"雪" 同音（xue）
    assert r2["homophones"] == ["雪"] and r2["score"] == 1.0   # 同音不算错
    r3 = check_segment(ref, "大青树下的校")      # "学"→"校"（xue≠xiao）→ 错字
    assert r3["wrong_chars"] == ["校"] and abs(r3["score"] - 6 / 7) < 1e-9


def test_missing_and_extra_and_fullwidth():
    r = check_segment("早上从山坡上走来", "早上山坡上走来")     # 漏"从"
    assert r["missing"] == ["从"]
    r = check_segment("早上走来", "早上走来了许多")            # 多字
    # W-T2 断言裁定：difflib 自然对齐 equal("早上走来")+insert("了许多")
    # → extra=["了","许","多"]（3 字）；简报原断言的 4 字两分支均不成立，
    # 修正为算法一致的最小期望（裁定详见 task-T9-report.md §4-1）。
    assert r["extra"] == ["了", "许", "多"]
    r = check_segment("共１２３只", "共123只")                # NFKC 全角→半角等价
    assert r["score"] == 1.0


def test_english_token_mode():
    r = check_segment("Good morning, Miss Liu!", "good morning miss liu",
                      lang="english")                          # token 序列 + lowercase + 去标点
    assert r["score"] == 1.0


def test_empty_input_is_all_missing():
    r = check_segment("你好世界", "")                          # 空输入段 = 整段漏字
    assert r["score"] == 0.0 and len(r["missing"]) == 4


def test_pypinyin_missing_degrades_to_wrong_char(monkeypatch):
    # 惰性导入钉住：pypinyin 缺失时同音判定降级为错字（不崩溃、不误判为对）
    monkeypatch.setitem(sys.modules, "pypinyin", None)
    r = check_segment("大青树下的小学", "大青树下的小雪")        # 1:1 替换 学→雪
    assert r["homophones"] == [] and r["wrong_chars"] == ["雪"]
    assert abs(r["score"] - 6 / 7) < 1e-9


def test_english_hyphen_cross_form_aligns():
    # 连字符跨书写形态对齐（T9 审查重要-1）：Pd 归一为空白而非删除，
    # "good-bye" 与 "good bye" 互为等价——一词差异不得放大为整句失配。
    assert check_segment("Good-bye, Miss Liu!", "good bye miss liu",
                         lang="english")["score"] == 1.0
    assert check_segment("I like ice-cream and cake", "i like ice cream and cake",
                         lang="english")["score"] == 1.0
