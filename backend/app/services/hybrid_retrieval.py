import logging
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "它", "他", "她", "们", "什么", "怎么", "哪", "哪些", "哪个",
    "请", "帮", "帮忙", "查询", "查", "显示", "列出", "获取", "得到", "找", "看看",
    "一下", "下", "把", "被", "让", "给", "跟", "和", "与", "及", "或", "但是", "而且",
    "因为", "所以", "如果", "虽然", "不过", "然后", "现在", "今天", "昨天", "明天",
    "这个", "那个", "这些", "那些", "多少", "几", "个", "种", "类",
    "需要", "想要", "希望", "能", "可以", "能够", "应该", "必须",
    "吗", "呢", "吧", "啊", "哦", "嗯", "呀",
}

_DOMAIN_PHRASES = [
    "电费", "电价", "电量", "电度", "电压", "电流", "功率", "容量", "需量",
    "户号", "户名", "表号", "电表", "电能表", "计量点", "计量装置",
    "变压器", "专线", "母线", "开关", "断路器",
    "峰谷", "尖峰", "平段", "低谷", "基本电费", "力调电费", "功率因数",
    "市场化", "零售", "批发", "直接交易", "输配电价", "上网电价",
    "结算", "账单", "发票", "欠费", "缴费", "收费",
    "用户", "客户", "用电", "供电", "售电", "购电",
    "最大需量", "合同容量", "运行容量", "计费容量", "抄表", "算费",
    "工业", "商业", "居民", "农业", "非工业", "大工业",
    "属性", "字段", "指标", "维度", "分类", "编码", "名称", "代码",
    "同比", "环比", "累计", "本月", "上月", "本年", "去年",
    "方案", "业务", "数据", "报表", "记录", "明细", "汇总",
    "用电客户", "用电户", "客户名称", "客户编号", "客户标识",
    "安装点", "受电点", "并网点", "计量箱",
    "装机容量", "核定容量", "合计容量", "申请容量", "铭牌容量",
    "实收金额", "应收金额", "收费金额", "欠费余额", "预收金额",
]

_SYNONYM_MAP = {
    "户号": ["户号", "客户编号", "用电户号", "用户编号", "客户代码"],
    "户名": ["户名", "客户名称", "用电户名称", "用户名称", "新客户名称"],
    "用电客户": ["用电客户", "电力客户", "用户", "客户", "用电户"],
    "客户标识": ["客户标识", "客户ID", "用户标识", "客户唯一标识"],
    "客户分类": ["客户分类", "用户分类", "客户类别", "用电类别"],
    "客户状态": ["客户状态", "用户状态", "用电状态", "销户状态"],
    "联系人": ["联系人", "联系方式", "客户联系人", "联系电话", "电话", "手机号", "手机", "联系手机"],
    "证件号": ["证件号", "身份证号", "证件号码", "证照号", "身份证", "证件类型", "证件代码"],
    "联系电话": ["联系电话", "电话", "联系方式", "手机号", "手机", "联系手机", "联系人"],
    "证件号码": ["证件号码", "证件号", "身份证号", "证照号", "身份证", "证件类型"],
    "证件类型": ["证件类型", "证件种类", "身份证类型", "证件名称"],
    "电话": ["电话", "联系电话", "联系方式", "手机号", "手机", "联系手机"],
    "手机号": ["手机号", "手机", "联系电话", "电话", "联系方式", "联系手机"],
    "用能地址": ["用能地址", "用电地址", "客户地址", "供电地址", "装表地址", "通讯地址", "安装地址"],
    "变压器": ["变压器", "配变", "专变", "变压器总容量"],
    "电表": ["电表", "电能表", "计量装置", "表计"],
    "断路器": ["断路器", "开关", "空开", "空气开关"],
    "专线": ["专线", "专用线路", "客户专线"],
    "母线": ["母线", "汇流排", "母排"],
    "互感器": ["互感器", "CT", "PT", "电流互感器", "电压互感器"],
    "隔离开关": ["隔离开关", "刀闸", "隔离刀闸"],
    "避雷器": ["避雷器", "防雷器", "过电压保护器"],
    "电容器": ["电容器", "补偿电容", "无功补偿装置"],
    "配电柜": ["配电柜", "开关柜", "配电箱"],
    "电缆": ["电缆", "线缆", "电力电缆"],
    "架空线": ["架空线", "架空线路", "导线"],
    "杆塔": ["杆塔", "电杆", "铁塔"],
    "绝缘子": ["绝缘子", "瓷瓶", "绝缘瓷瓶"],
    "熔断器": ["熔断器", "保险丝", "熔丝"],
    "表箱": ["表箱", "计量箱", "电表箱"],
    "采集终端": ["采集终端", "集中器", "采集器"],
    "用电量": ["用电量", "电量", "有功电量"],
    "有功功率": ["有功功率", "有功", "实时功率", "有功负荷"],
    "无功功率": ["无功功率", "无功", "无功负荷"],
    "功率因数": ["功率因数", "力率", "cosφ"],
    "视在功率": ["视在功率", "视在负荷", "总功率"],
    "无功电量": ["无功电量", "无功电能", "无功电度"],
    "有功电量": ["有功电量", "有功电能", "有功电度"],
    "峰电量": ["峰电量", "峰段电量", "高峰电量"],
    "谷电量": ["谷电量", "谷段电量", "低谷电量"],
    "平电量": ["平电量", "平段电量", "平时段电量"],
    "尖峰电量": ["尖峰电量", "尖段电量"],
    "总电量": ["总电量", "总用电量", "合计电量"],
    "日用电量": ["日用电量", "日电量", "日用电"],
    "月用电量": ["月用电量", "月电量", "月用电"],
    "年用电量": ["年用电量", "年电量", "年用电"],
    "负荷": ["负荷", "负载", "用电负荷"],
    "最大负荷": ["最大负荷", "峰值负荷", "最高负荷"],
    "最小负荷": ["最小负荷", "谷值负荷", "最低负荷"],
    "平均负荷": ["平均负荷", "均负荷"],
    "负荷率": ["负荷率", "负载率"],
    "电流": ["电流", "线电流", "相电流"],
    "频率": ["频率", "电网频率", "工频"],
    "电费": ["电费", "电度电费", "基本电费"],
    "电价": ["电价", "单价", "度电价"],
    "欠费": ["欠费", "欠费余额", "未缴电费"],
    "缴费": ["缴费", "交费", "收费"],
    "基本电费": ["基本电费", "容量电费", "需量电费"],
    "力调电费": ["力调电费", "功率因数调整电费", "力率电费"],
    "电度电费": ["电度电费", "电量电费"],
    "峰谷电费": ["峰谷电费", "分时电费"],
    "应收电费": ["应收电费", "应收金额", "应缴电费"],
    "实收电费": ["实收电费", "实收金额", "实缴电费"],
    "预收电费": ["预收电费", "预收金额", "预存电费"],
    "退费": ["退费", "退款", "电费退还"],
    "违约金": ["违约金", "滞纳金", "电费违约金"],
    "峰电价": ["峰电价", "峰段电价", "高峰电价"],
    "谷电价": ["谷电价", "谷段电价", "低谷电价"],
    "平电价": ["平电价", "平段电价"],
    "尖峰电价": ["尖峰电价", "尖段电价"],
    "输配电价": ["输配电价", "配电价格"],
    "上网电价": ["上网电价", "发电上网价"],
    "销售电价": ["销售电价", "售电价格"],
    "计量点": ["计量点", "计量装置", "电表"],
    "抄表": ["抄表", "采集", "读数"],
    "倍率": ["倍率", "综合倍率", "CT变比"],
    "表号": ["表号", "电表号", "电能表编号", "资产编号"],
    "表底": ["表底", "表码", "电表示数"],
    "正向有功": ["正向有功", "正向有功电量"],
    "反向有功": ["反向有功", "反向有功电量"],
    "正向无功": ["正向无功", "正向无功电量"],
    "反向无功": ["反向无功", "反向无功电量"],
    "抄表日期": ["抄表日期", "抄表时间", "采集日期"],
    "计量方式": ["计量方式", "计量类型"],
    "接线方式": ["接线方式", "接线方法"],
    "安装点": ["安装点", "受电点", "并网点"],
    "装机容量": ["装机容量", "核定容量", "合同容量"],
    "运行容量": ["运行容量", "实际容量"],
    "需量": ["需量", "最大需量", "最高需量"],
    "合同容量": ["合同容量", "约定容量", "协议容量"],
    "申请容量": ["申请容量", "报装容量"],
    "铭牌容量": ["铭牌容量", "额定容量"],
    "计费容量": ["计费容量", "计容"],
    "合计容量": ["合计容量", "总容量"],
    "最大需量": ["最大需量", "最高需量", "峰值需量"],
    "实际需量": ["实际需量", "实测需量"],
    "线损": ["线损", "线路损耗", "网损"],
    "线损率": ["线损率", "损耗率"],
    "供电量": ["供电量", "输入电量"],
    "售电量": ["售电量", "销售电量"],
    "损失电量": ["损失电量", "损耗电量"],
    "电压": ["电压", "端电压", "线电压"],
    "相电压": ["相电压", "对地电压"],
    "额定电压": ["额定电压", "标称电压"],
    "电压偏差": ["电压偏差", "电压偏移"],
    "电压合格率": ["电压合格率"],
    "结算": ["结算", "算费", "出账"],
    "账单": ["账单", "电费账单", "结算单"],
    "发票": ["发票", "电费发票", "增值税发票"],
    "抄表段": ["抄表段", "抄表区", "抄表册"],
    "核算": ["核算", "电费核算", "电费计算"],
    "业扩": ["业扩", "业扩报装", "新装增容"],
    "报装": ["报装", "用电申请", "新装"],
    "增容": ["增容", "扩容", "增加容量"],
    "销户": ["销户", "注销", "拆表销户"],
    "过户": ["过户", "更名", "客户更名"],
    "暂停": ["暂停", "暂停用电", "报停"],
    "复电": ["复电", "恢复用电", "送电"],
    "大工业": ["大工业", "工业用电"],
    "商业": ["商业", "商业用电", "一般工商业"],
    "居民": ["居民", "居民用电", "生活用电"],
    "农业": ["农业", "农业用电", "排灌"],
    "非工业": ["非工业", "非工业用电"],
    "普通工业": ["普通工业", "普通工业用电"],
    "趸售": ["趸售", "趸售用电", "批发"],
    "峰谷分时": ["峰谷分时", "分时电价", "峰谷电价"],
    "本月": ["本月", "当月", "这个月"],
    "上月": ["上月", "上个月"],
    "本年": ["本年", "今年", "当年"],
    "去年": ["去年", "上一年"],
    "同比": ["同比", "较去年同期"],
    "环比": ["环比", "较上期"],
    "累计": ["累计", "总计", "合计"],
}

_SYNONYM_CACHE: Dict[str, Any] = {"loaded_at": 0.0, "ttl": 300.0}


def load_synonyms_from_db(db: Session) -> None:
    global _SYNONYM_MAP
    now = time.time()
    if now - _SYNONYM_CACHE["loaded_at"] < _SYNONYM_CACHE["ttl"]:
        return
    try:
        from app.models.base import SynonymGroup
        rows = db.query(SynonymGroup).filter(SynonymGroup.enabled == True).all()
        merged = dict(_SYNONYM_MAP)
        for row in rows:
            term = (row.standard_term or "").strip()
            if not term:
                continue
            syns = row.synonyms if isinstance(row.synonyms, list) else []
            cleaned = [str(s).strip() for s in syns if str(s or "").strip()]
            if not cleaned:
                continue
            if term in merged:
                existing = list(merged[term])
                for s in cleaned:
                    if s not in existing:
                        existing.append(s)
                merged[term] = existing
            else:
                merged[term] = [term] + [s for s in cleaned if s != term]
        _SYNONYM_MAP = merged
        _SYNONYM_CACHE["loaded_at"] = now
        logger.info("load_synonyms_from_db merged=%d db_rows=%d", len(merged), len(rows))
    except Exception as e:
        logger.warning("load_synonyms_from_db failed: %s", e)

_DOMAIN_PHRASE_SET = set(_DOMAIN_PHRASES)

_jieba_initialized = False


def _ensure_jieba() -> None:
    global _jieba_initialized
    if _jieba_initialized:
        return
    try:
        import jieba
        for w in _DOMAIN_PHRASES:
            jieba.add_word(w)
        jieba.initialize()
        _jieba_initialized = True
    except ImportError:
        logger.warning("jieba not installed, fallback to simple split")


_DIGIT_UNIT_RE = re.compile(r"^[\d零一二三四五六七八九十百千万亿\.]+[号年月日个户块元度千瓦瓦安伏兆]?$")


def tokenize_query(query_text: str) -> List[str]:
    if not query_text:
        return []
    _ensure_jieba()
    text = query_text.strip()
    tokens: List[str] = []

    chunks = re.split(r"[，。、；：！？\s,;:!?\(\)（）\[\]【】]+", text)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            import jieba
            words = jieba.cut(chunk, cut_all=False)
        except Exception:
            words = [chunk]

        current = []
        for w in words:
            w = w.strip()
            if not w:
                continue
            if w in _STOP_WORDS:
                continue
            if len(w) == 1 and w not in _DOMAIN_PHRASE_SET and not re.search(r"[\d]", w):
                continue
            if _DIGIT_UNIT_RE.match(w):
                tokens.append(w)
                continue
            if w in _DOMAIN_PHRASE_SET:
                tokens.append(w)
                continue
            current.append(w)

        if current:
            tokens.extend(current)

    if not tokens:
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk and chunk not in _STOP_WORDS and len(chunk) > 1:
                tokens.append(chunk)

    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _normalize_score(sim: float) -> float:
    return (sim + 1) / 2


def hybrid_search(
    db: Session,
    query_text: str,
    *,
    top_k: int = 10,
    term_types: Optional[List[str]] = None,
    entity_scope: str = "data",
    per_token_top_k: int = 20,
    exact_match_bonus: float = 0.35,
    multi_hit_bonus: float = 0.12,
    full_query_weight: float = 0.55,
    token_weight: float = 0.45,
) -> List[Dict[str, Any]]:
    from app.services.standard_semantic_qdrant import (
        QDRANT_COLLECTION_STANDARD_TERMS,
        get_standard_semantic_collection,
        query_standard_semantic_matches_qdrant,
    )
    from app.services.semantic_retrieval import get_or_init_retrieval_config

    started_at = time.time()

    load_synonyms_from_db(db)

    tokens = tokenize_query(query_text)
    logger.info("hybrid_search query=%r tokens=%s", query_text, tokens)

    cfg = get_or_init_retrieval_config(db)
    collection = get_standard_semantic_collection(cfg.get("vector_model_name"))

    scope = (entity_scope or "data").lower()

    full_rows: List[Dict[str, Any]] = []
    full_rows = query_standard_semantic_matches_qdrant(
        db,
        query_text,
        top_k=max(top_k * 2, 30),
        term_types=term_types,
        entity_scope=entity_scope,
        collection=collection,
    )
    for r in full_rows:
        r["_source"] = "full"
        r["_full_score"] = float(r.get("score") or 0.0)

    token_rows_map: Dict[str, List[Dict[str, Any]]] = {}
    for tok in tokens[:12]:
        try:
            rows = query_standard_semantic_matches_qdrant(
                db,
                tok,
                top_k=per_token_top_k,
                term_types=term_types,
                entity_scope=entity_scope,
                collection=collection,
            )
            token_rows_map[tok] = rows
        except Exception as e:
            logger.warning("hybrid token search failed tok=%r: %s", tok, e)
            token_rows_map[tok] = []

    merged: Dict[str, Dict[str, Any]] = {}

    for r in full_rows:
        tid = r.get("term_id") or r.get("attribute_id") or r.get("entity_id")
        if not tid:
            continue
        if tid not in merged:
            merged[tid] = dict(r)
            merged[tid]["_hit_tokens"] = []
            merged[tid]["_token_scores"] = []
            merged[tid]["_exact_matched"] = False
        merged[tid]["_full_score"] = float(r.get("_full_score") or r.get("score") or 0.0)

    for tok, rows in token_rows_map.items():
        for r in rows:
            tid = r.get("term_id") or r.get("attribute_id") or r.get("entity_id")
            if not tid:
                continue
            if tid not in merged:
                merged[tid] = dict(r)
                merged[tid]["_hit_tokens"] = []
                merged[tid]["_token_scores"] = []
                merged[tid]["_exact_matched"] = False
                merged[tid]["_full_score"] = 0.0
            merged[tid]["_hit_tokens"].append(tok)
            merged[tid]["_token_scores"].append(float(r.get("score") or 0.0))

            payload = r.get("text_payload") or {}
            attr_name = (payload.get("attribute_name") or r.get("attribute_name") or "").strip()
            term = (payload.get("term") or r.get("term") or "").strip()
            search_texts = payload.get("search_texts") or []
            entity_name = (payload.get("entity_name") or r.get("entity_name") or "").strip()

            tok_syns = set()
            tok_syns.add(tok)
            if tok in _SYNONYM_MAP:
                tok_syns.update(_SYNONYM_MAP[tok])

            matched = False
            for field_val in [attr_name, term, entity_name]:
                if not field_val:
                    continue
                for syn in tok_syns:
                    if syn == field_val or syn in field_val:
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                for st in search_texts:
                    s = str(st or "").strip()
                    if not s:
                        continue
                    for syn in tok_syns:
                        if syn in s:
                            matched = True
                            break
                    if matched:
                        break
            if matched:
                merged[tid]["_exact_matched"] = True

    results: List[Dict[str, Any]] = []
    for tid, r in merged.items():
        full_score = float(r.get("_full_score") or 0.0)
        token_scores = r.get("_token_scores") or []
        token_avg = sum(token_scores) / len(token_scores) if token_scores else 0.0
        token_max = max(token_scores) if token_scores else 0.0
        token_component = token_max * 0.6 + token_avg * 0.4

        combined = full_query_weight * full_score + token_weight * token_component

        hit_count = len(r.get("_hit_tokens") or [])
        if hit_count > 1:
            combined += multi_hit_bonus * (hit_count - 1)
        if r.get("_exact_matched"):
            combined += exact_match_bonus

        combined = min(combined, 1.0)

        r["score"] = round(combined, 6)
        r["vector_sim"] = round(float(r.get("vector_sim") or full_score), 6)
        r["hybrid_hit_tokens"] = r.get("_hit_tokens") or []
        r["hybrid_token_count"] = hit_count
        r["hybrid_exact_match"] = bool(r.get("_exact_matched"))
        r["hybrid_full_score"] = round(full_score, 6)
        r["hybrid_token_score"] = round(token_component, 6)

        for k in ("_hit_tokens", "_token_scores", "_exact_matched", "_full_score", "_source"):
            r.pop(k, None)

        results.append(r)

    results.sort(key=lambda x: -x["score"])
    results = results[:top_k]

    elapsed_ms = int((time.time() - started_at) * 1000)
    logger.info(
        "hybrid_search tokens=%d full_rows=%d merged=%d returned=%d took=%dms",
        len(tokens),
        len(full_rows),
        len(merged),
        len(results),
        elapsed_ms,
    )
    return results


__all__ = ["tokenize_query", "hybrid_search", "load_synonyms_from_db", "_SYNONYM_MAP"]
