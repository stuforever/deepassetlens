#!/usr/bin/env python3
"""Elasticsearch 索引初始化：从 backend/data/init/es/ 导入 mapping + data。

用法（在 backend 目录执行）：
    ES_PASSWORD=infini_rag_flow python data/init/init_es.py

环境变量：
    ES_HOST     ES 地址（默认 http://localhost:11200）
    ES_USER     用户名（默认 elastic）
    ES_PASSWORD 密码
"""
import json
import os
import sys
from pathlib import Path

import requests

ES_HOST = os.getenv("ES_HOST", "http://localhost:11200").rstrip("/")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASS = os.getenv("ES_PASSWORD", "")
ES_DIR = Path(__file__).parent / "es"

AUTH = (ES_USER, ES_PASS) if ES_USER else None
HEADERS = {"Content-Type": "application/json"}


def put_index(name: str, mapping_file: Path) -> bool:
    raw = json.loads(mapping_file.read_text(encoding="utf-8"))
    body = raw.get(name, raw)  # {index_name: {mappings, settings, aliases}} 或直接 body
    r = requests.put(f"{ES_HOST}/{name}", headers=HEADERS, json=body, auth=AUTH)
    ok = r.status_code in (200, 201)
    print(f"  create index {name}: {'OK' if ok else 'FAIL ' + str(r.status_code)}")
    if not ok:
        print(f"    {r.text[:300]}")
    return ok


def bulk_index(name: str, data_file: Path) -> int:
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    # 兼容多种备份格式：{hits:{hits:[{_id,_source}]}} / {hits:[...]} / [源对象...]
    hits = []
    if isinstance(raw, dict):
        h = raw.get("hits")
        if isinstance(h, dict):
            hits = h.get("hits", [])
        elif isinstance(h, list):
            hits = h
    elif isinstance(raw, list):
        hits = raw
    if not hits:
        print(f"  index {name}: no docs")
        return 0
    lines = []
    for h in hits:
        if isinstance(h, dict):
            _id = h.get("_id")
            src = h.get("_source", h)
        else:
            _id, src = None, h
        action = {"index": {"_index": name}}
        if _id is not None:
            action["index"]["_id"] = _id
        lines.append(json.dumps(action, ensure_ascii=False))
        lines.append(json.dumps(src, ensure_ascii=False))
    body = "\n".join(lines) + "\n"
    r = requests.post(
        f"{ES_HOST}/_bulk",
        headers={"Content-Type": "application/x-ndjson"},
        data=body.encode("utf-8"),
        auth=AUTH,
    )
    ok = r.status_code in (200, 201)
    cnt = len(hits)
    print(f"  index {name}: {cnt} docs -> {'OK' if ok else 'FAIL ' + str(r.status_code)}")
    if not ok:
        print(f"    {r.text[:300]}")
    return cnt if ok else 0


def main():
    if not ES_DIR.exists():
        print(f"ES 数据目录不存在: {ES_DIR}", file=sys.stderr)
        sys.exit(1)
    mapping_files = sorted(ES_DIR.glob("*_mapping.json"))
    if not mapping_files:
        print(f"未找到 *_mapping.json: {ES_DIR}", file=sys.stderr)
        sys.exit(1)
    print(f"ES_HOST={ES_HOST}  索引数={len(mapping_files)}")
    total = 0
    for mf in mapping_files:
        idx = mf.name.replace("_mapping.json", "")
        if put_index(idx, mf):
            data_file = ES_DIR / f"{idx}_data.json"
            if data_file.exists():
                total += bulk_index(idx, data_file)
    requests.post(f"{ES_HOST}/_refresh", auth=AUTH)
    print(f"\nES 初始化完成，共导入 {total} 条文档。")


if __name__ == "__main__":
    main()
