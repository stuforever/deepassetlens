# -*- coding: utf-8 -*-
"""intent_classifier.py - 意图分类纯规则单模块（批6-R2 收拢，问二）

路由（SkillRouter）、指引预载（query_contract/批2-E）、模板直出（direct_pipeline/批9）
三处共用同一套判定词表与函数，消除散落各处的关键词列表。

立场不变：全部**纯规则确定性**判定——权限边界不交给采样（R3 轻量 LLM 路由继续不做）。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 词表（单一事实源；skill_router/query_contract/direct_pipeline 一律从这里取）
# ---------------------------------------------------------------------------

# S1 稳定性攻坚（L1）：聚合分布意图触发词——命中即要求 GROUP BY 聚合视图，禁止返回明细全表
AGGREGATE_TRIGGERS: Tuple[str, ...] = ("分布", "占比", "构成", "比例", "合计", "汇总", "分组", "分别")

# S2（金标扩容）：聚合分布维度词 -> 目标列提示（dimension_hint）。
# 解决「各行业的用电客户分布」这类维度不在 agent 规范明细视图内的聚合退化：
# 路由层命中聚合触发词且文本含已知维度词时，契约给列名提示（结构保障，不依赖模型猜列）。
DIMENSION_HINT_MAP: Tuple[Tuple[str, str], ...] = (
    ("电压等级", "voltage_name"),
    ("重要性等级", "impt_lv_name"),
    ("行业", "ind_cls_name"),
    ("用电类别", "ec_categ_name"),
    ("客户分类", "cust_cls_name"),
    ("管理单位", "mgt_org_name"),
    ("城乡类别", "urbanrural_categ_name"),
    ("负荷性质", "load_char_name"),
    ("用电状态", "ecc_stat_name"),
    ("状态", "ecc_stat_name"),
)

# S2（金标扩容）：歧义意图检测词表——命中模糊词且无明确查询意图词 -> 须澄清而非乱查
VAGUE_MARKERS: Tuple[str, ...] = ("情况", "怎么样", "如何", "分析一下", "看看", "了解一下", "介绍", "大概", "概览", "评估一下")
CLEAR_QUERY_MARKERS: Tuple[str, ...] = (
    "多少", "分布", "占比", "构成", "比例", "合计", "汇总", "分组", "分别",
    "列出", "清单", "有哪些", "排序", "最大", "最小", "大于", "小于", "等于",
    "超过", "数量", "总数", "统计", "过滤", "哪个", "谁", "前", "按", "每个",
    "分布情况", "多少户", "多少条", "的客户", "用户", "客户名", "名称", "容量", "电压等级",
    "重要性", "管理单位", "安装点", "台区", "计量", "电能表", "合同",
    # 批13-R2：对比类是明确分析意图（如「预算已分配金额和总额的对比情况」），
    # 不应因句尾「情况」被误判歧义强制澄清
    "对比", "相比", "执行率", "差异", "偏差", "余额",
)

# 计数类触发词（批9 模板直出判定 + 计数同义归一化共用语义）
COUNT_WORDS: Tuple[str, ...] = ("总数", "数量", "多少个", "几个", "多少", "数目", "计数")

# 排名/TopN 类触发词
TOPN_WORDS: Tuple[str, ...] = ("排名", "最大", "最多", "最少", "最小", "最高", "最低", "top", "Top", "TOP")

# 动态条件词（批9 直出排除项）：比较/过滤类
CONDITION_WORDS: Tuple[str, ...] = ("大于", "超过", "以上", "以下", "高于", "低于", "不小于",
                                    "大于等于", "小于", "区间", "范围内", "多于", "等于")
# 动态条件：日期/时间相对词
_DATE_WORDS: Tuple[str, ...] = ("今天", "昨天", "本月", "上月", "今年", "去年", "近期", "最新", "上个月", "去年今日")
_DATE_PATTERN = re.compile(r"\d{4}\s*年|\d{1,2}\s*月|\d{4}[-/.]\d{1,2}")
# 动态条件：具体编号/ID 形态（CUS0001、P-2024-001 等）与引号内具体值
_ID_PATTERN = re.compile(r"[A-Za-z]{2,}[-_]?\d+|「[^」]+」|\"[^\"]+\"|“[^”]+”")

# 指引预载规则（批2-E 移入）：(小节标题前缀, 触发词) 按序判定；命中即摘录对应小节
GUIDANCE_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("聚合类", ("数量", "总数", "多少", "统计", "几个", "平均", "总和", "总计", "分组", "占比", "分布", "比例", "百分比")),
    ("排名类", ("排名", "前", "最大", "最多", "最少", "top", "Top")),
    ("趋势类", ("同比", "环比", "趋势", "逐月", "逐季", "增长率")),
    ("对比类", ("对比", "相比", "哪个多", "哪个少")),
    ("质检类", ("空值", "重复", "异常", "质检", "缺失", "完整性")),
)


# ---------------------------------------------------------------------------
# 判定函数（与原 skill_router 行为逐字一致的部分保持一致）
# ---------------------------------------------------------------------------

def detect_aggregate_intent(text: str) -> Optional[Dict[str, Any]]:
    """识别聚合分布/占比/构成类意图。命中 -> aggregate_intent dict；否则 None。"""
    if not text:
        return None
    hit = [t for t in AGGREGATE_TRIGGERS if t in text]
    if not hit:
        return None
    dim_hint = None
    for _w, _col in DIMENSION_HINT_MAP:
        if _w in text:
            dim_hint = _col
            break
    return {
        "trigger": hit[0],
        "dimension_hint": dim_hint,  # 命中已知维度词 -> 目标列提示（行业->ind_cls_name 等）
        "required_shape": "GROUP BY 维度列 + COUNT/SUM",
    }


def detect_vague_intent(text: str) -> bool:
    """歧义检测：含模糊词且无明确查询意图词 -> True（触发澄清）。"""
    if not text:
        return False
    if any(m in text for m in CLEAR_QUERY_MARKERS):
        return False
    return any(v in text for v in VAGUE_MARKERS)


def is_count_intent(text: str) -> bool:
    """计数类问法（批9 直通判定）：含计数词且无聚合/排名触发。

    「统计用电客户数量」「用电客户有多少个」-> True；
    「各电压等级客户占比」（聚合）/「容量最大的客户」（排名）-> False。
    """
    t = str(text or "").strip()
    if not t:
        return False
    if any(w in t for w in AGGREGATE_TRIGGERS) or any(w in t for w in TOPN_WORDS):
        return False
    return any(w in t for w in COUNT_WORDS)


def has_dynamic_condition(text: str) -> bool:
    """动态条件检测（批9 直通排除项，纯规则）：比较/过滤词、日期时间词、
    具体日期形态、具体编号/ID/引号值 -> True（示例 SQL 无法覆盖动态槽位）。"""
    t = str(text or "")
    if not t:
        return False
    if any(w in t for w in CONDITION_WORDS):
        return True
    if any(w in t for w in _DATE_WORDS):
        return True
    if _DATE_PATTERN.search(t):
        return True
    if _ID_PATTERN.search(t):
        return True
    return False


def classify_intent(text: str) -> str:
    """主意图分类（单标签）：vague > aggregate > topn > trend > quality > compare > count > other。

    三处共用：路由调试/指引预载/模板直出。返回英文类别名（稳定枚举，勿改拼写）。
    """
    t = str(text or "").strip()
    if not t:
        return "other"
    if detect_vague_intent(t):
        return "vague"
    if any(w in t for w in AGGREGATE_TRIGGERS):
        return "aggregate"
    if any(w in t for w in TOPN_WORDS):
        return "topn"
    if any(w in t for w in ("同比", "环比", "趋势", "逐月", "逐季", "增长率")):
        return "trend"
    if any(w in t for w in ("空值", "重复", "异常", "质检", "缺失", "完整性")):
        return "quality"
    if any(w in t for w in ("对比", "相比", "哪个多", "哪个少")):
        return "compare"
    if is_count_intent(t):
        return "count"
    return "other"


def guidance_labels_for(text: str) -> List[str]:
    """指引预载（批2-E）小节标签判定：按 GUIDANCE_RULES 顺序返回命中的小节标题前缀。"""
    q = str(text or "").strip()
    if not q:
        return []
    picked = [_label for _label, _words in GUIDANCE_RULES if any(w in q for w in _words)]
    return list(dict.fromkeys(picked))


# ---------------------------------------------------------------------------
# 批13-J R3：否定模式检测（路由治理）——命中触发词但句内明确否定时不触发该场景
# ---------------------------------------------------------------------------

# 否定标记词（紧邻触发词前/后 N 字内才视为否定；避免「排除/别」等与业务语义冲突）
NEGATION_MARKERS: Tuple[str, ...] = ("不要", "别", "不查", "不用", "无需", "排除", "去掉", "不算", "不看", "别查", "不是")
_NEG_WINDOW = 4  # 否定词与触发词之间的最大字符距离（含否定词本身）


def has_negation(text: str, keyword: str) -> bool:
    """批13-J R3：句内否定模式检测——否定标记词出现在触发词前后 _NEG_WINDOW 字符内则视为否定。

    例：
      "不要查台区" -> "台区" 前有「不要」-> True（不触发台区场景）
      "排除掉这些" -> "这些" 前有「排除」-> True
      "统计用电客户数量" -> 无否定词 -> False（正常触发）
    """
    t = str(text or "")
    k = str(keyword or "")
    if not t or not k:
        return False
    idx = t.find(k)
    if idx < 0:
        return False
    # 否定词在触发词前：取触发词左侧窗口
    left = t[max(0, idx - _NEG_WINDOW):idx]
    for neg in NEGATION_MARKERS:
        if neg in left:
            return True
    # 否定词在触发词后：取触发词右侧窗口（如「台区不要查」）
    right = t[idx + len(k):idx + len(k) + _NEG_WINDOW]
    for neg in NEGATION_MARKERS:
        if neg in right:
            return True
    return False
