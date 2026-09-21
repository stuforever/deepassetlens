"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import difflib
import re
import unicodedata

__all__ = ["check_segment", "normalize"]

_ENGLISH_LANGS = {"english", "en"}


def _is_english(lang: str) -> bool:
    return str(lang).strip().lower() in _ENGLISH_LANGS


def _is_punct(ch: str) -> bool:
    return unicodedata.category(ch).startswith("P")


def _same_pinyin(a: str, b: str) -> bool:
    """无声调拼音比对（声调恒忽略）。pypinyin 惰性导入，缺失时降级为「不同音」。

    缺失降级意味着同音字会被判为错字而非同音——宁可错杀不误放行，
    且不阻塞匹配引擎在未装 pypinyin 的环境下运行。
    """
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return False
    return "".join(lazy_pinyin(a)) == "".join(lazy_pinyin(b))


def normalize(s: str, lang: str = "chinese") -> list[str]:
    """归一化为判定单元序列：中文按字、英语按 token。

    步骤：NFKC（全角→半角等价）→ 去中英标点（Unicode P* 类）；
    英语另做 lowercase + 按空白 token 切分；中文去全部空白。
    """
    s = unicodedata.normalize("NFKC", s)
    if _is_english(lang):
        s = s.lower()
        # 连字符类（Pd）归一为空白而非删除：跨 "good-bye"/"good bye" 书写形态
        # 对齐（T9 审查重要-1——删除会使一词差异在短句上放大为整句失配）
        s = re.sub(r"[\u002d\u2010-\u2015]", " ", s)
    # 去标点（保留空白：英语分词依赖空白，中文在最后统一去掉）
    s = "".join(ch for ch in s if not _is_punct(ch))
    if _is_english(lang):
        return s.split()
    return [ch for ch in s if not ch.isspace()]


def check_segment(ref: str, got: str, lang: str = "chinese") -> dict:
    """判定一段背诵/默写：返回 score 与五类判定结果。

    返回 dict 键：
        score        — (正确 + 同音) / 原文归一化总单元数
        wrong_chars  — 🔴 错字（录侧字）
        homophones   — 🟡 同音字（录侧字，声调恒忽略，不算错）
        missing      — ➖ 漏字（原文侧）
        extra        — ➕ 多字（录侧）
    """
    ref_norm = normalize(ref, lang)
    got_norm = normalize(got, lang)
    wrong_chars: list[str] = []
    homophones: list[str] = []
    missing: list[str] = []
    extra: list[str] = []

    if not ref_norm:
        # 空原文：无字可对——背录为空即满分，否则全部计多
        return {
            "score": 1.0 if not got_norm else 0.0,
            "wrong_chars": wrong_chars,
            "homophones": homophones,
            "missing": missing,
            "extra": list(got_norm),
        }

    correct = 0
    # autojunk=False：关闭 ≥200 单元序列的高频字剔除启发（长课文里
    # "的/了/是" 等高频字若被当 junk 会被整段误判），保持确定性对齐。
    matcher = difflib.SequenceMatcher(None, ref_norm, got_norm, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            correct += i2 - i1
        elif tag == "delete":
            missing.extend(ref_norm[i1:i2])
        elif tag == "insert":
            extra.extend(got_norm[j1:j2])
        elif tag == "replace":
            ref_part = ref_norm[i1:i2]
            got_part = got_norm[j1:j2]
            n = min(len(ref_part), len(got_part))
            # 块内右侧对齐（got 尾部对 ref 尾部）：背诵在出错点后收尾，
            # 尾字对尾字才还原 "学→雪/校" 这类真实替换对；若左侧对齐会把
            # "小学"↔"雪" 错配成 小↔雪（xiao≠xue），同音判定即失效。
            ref_tail = ref_part[len(ref_part) - n:]
            got_tail = got_part[len(got_part) - n:]
            for ref_ch, got_ch in zip(ref_tail, got_tail):
                if _same_pinyin(ref_ch, got_ch):
                    homophones.append(got_ch)
                else:
                    wrong_chars.append(got_ch)
            if len(got_part) > n:
                # got 侧块内剩余（前段）：区域不齐处多出的字 → 多
                extra.extend(got_part[:len(got_part) - n])
            if len(ref_part) > n:
                # ref 侧块内剩余（前段）：区域已被背录覆盖但长度不齐，
                # 按简报断言裁定（同音用例 score==1.0）不计罚——不入
                # missing/wrong，计入正确数。
                correct += len(ref_part) - n

    score = (correct + len(homophones)) / len(ref_norm)
    return {
        "score": score,
        "wrong_chars": wrong_chars,
        "homophones": homophones,
        "missing": missing,
        "extra": extra,
    }
