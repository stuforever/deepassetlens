# -*- coding: utf-8 -*-
import json
import time
from pathlib import Path
from urllib.request import urlopen

cache = Path(__file__).parent / "dt_baseline" / "_openapi_cache.json"
t0 = time.time()
spec = json.loads(urlopen("http://127.0.0.1:28000/openapi.json", timeout=180).read())
cache.write_text(json.dumps(spec), encoding="utf-8")
print(f"fetched in {time.time()-t0:.1f}s, paths={len(spec.get('paths', {}))}")
raw = "/api/v1/mother-questions/{mid}/review/submit"
print("raw in paths:", raw in spec["paths"])
be = set()
for p in spec.get("paths", {}).keys():
    be.add("/".join("{}".format(s) if s.startswith("{") else s for s in p.split("/")))
print("norm in be:", "/api/v1/mother-questions/{}/review/submit" in be)
p = "/api/v1/mother-questions/{mid}/review/submit"
got = "/".join("{}".format(s) if s.startswith("{") else s for s in p.split("/"))
print("got:", repr(got))
print("expected:", repr("/api/v1/mother-questions/{}/review/submit"))
print("equal:", got == "/api/v1/mother-questions/{}/review/submit")
seg = "{mid}"
print("seg repr:", repr(seg), "startswith:", seg.startswith("{"))
print("format:", repr("{}".format(seg)))
print("lambda join:", repr("/".join(("{}".format(s) if s.startswith("{") else s) for s in p.split("/"))))
print("norm in be (chapters):", "/api/v1/curriculum/chapters/{}" in be)
