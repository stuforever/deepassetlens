"""将 ES 宽表 tupu_dwd_cust_analog_p（96列 v0000-v2345）UNPIVOT 成窄表 vw_cust_power_ts。

背景：distribution-overload 剧本需要窄表格式（inst_id, date, occur_time, power）做
连续天数/负载率统计。ES 宽表是原始数据（每条一天96点），窄表是展开后每条一个时间点。
Doris 2.1.8 不支持 UNPIVOT 语法，因此在导入时展开。

执行：cd backend && python -m data.init.init_es_power_ts
"""
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk

ES_URL = "http://localhost:11200"
ES_USER = "elastic"
ES_PASS = "infini_rag_flow"
SRC_INDEX = "tupu_dwd_cust_analog_p"   # ES 已有宽表（912条×96列）
DST_INDEX = "vw_cust_power_ts"          # 新窄表索引（每条一个时间点）

# 96 个时间点列名 v0000-v2345（每15分钟一个点）
TIME_COLS = [f"v{h:02d}{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

MAPPING = {
    "mappings": {
        "properties": {
            "inst_id": {"type": "keyword"},
            "equip_src_id": {"type": "keyword"},
            "measuerment_type": {"type": "keyword"},
            "date": {"type": "keyword"},
            "occur_time": {"type": "keyword"},
            "power": {"type": "double"},
        }
    },
}


def main():
    es = Elasticsearch(ES_URL, basic_auth=(ES_USER, ES_PASS))

    # 删旧索引（幂等）
    if es.indices.exists(index=DST_INDEX):
        es.indices.delete(index=DST_INDEX)
        print(f"已删除旧索引 {DST_INDEX}")

    # 建新索引（窄表 mapping）
    es.indices.create(index=DST_INDEX, **MAPPING)
    print(f"已创建索引 {DST_INDEX}（窄表：inst_id/date/occur_time/power）")

    total_in = 0
    total_out = 0

    def gen_actions():
        nonlocal total_in, total_out
        for hit in scan(es, index=SRC_INDEX, query={"query": {"match_all": {}}}):
            total_in += 1
            src = hit["_source"]
            inst_id = src.get("inst_id")
            equip_src_id = src.get("equip_src_id")
            measuerment_type = src.get("measuerment_type")
            date = src.get("date")
            for col in TIME_COLS:
                power = src.get(col)
                if power is None:
                    continue
                total_out += 1
                yield {
                    "_index": DST_INDEX,
                    "_source": {
                        "inst_id": inst_id,
                        "equip_src_id": equip_src_id,
                        "measuerment_type": measuerment_type,
                        "date": date,
                        "occur_time": col,        # 'v0000'..'v2345'，字符串排序即时间序
                        "power": float(power),
                    },
                }

    success, errors = bulk(es, gen_actions(), chunk_size=5000, request_timeout=120, raise_on_error=False)
    es.indices.refresh(index=DST_INDEX)
    print(f"读取 {total_in} 条宽表 -> 写入 {total_out} 条窄表（成功 {success}，失败 {len(errors)}）")
    if errors[:3]:
        for e in errors[:3]:
            print(f"  错误样例: {e}")

    # 验证
    count = es.count(index=DST_INDEX)["count"]
    print(f"索引 {DST_INDEX} 最终文档数: {count}")
    # 样例
    sample = es.search(index=DST_INDEX, size=2, query={"match_all": {}})
    for hit in sample["hits"]["hits"]:
        print(f"  样例: {hit['_source']}")


if __name__ == "__main__":
    main()
