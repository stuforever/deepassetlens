# -*- coding: utf-8 -*-
"""修正 provider property_mappings：openid+profile+email+groups 四件套齐。"""
import requests

h = {"Authorization": "Bearer deepassetlens_bootstrap_token_2026"}
B = "http://localhost:9100/api/v3"

rows = requests.get(B + "/propertymappings/provider/scope/", headers=h, timeout=10).json()["results"]
want = ("scope-openid", "scope-profile", "scope-email")
pks = [m["pk"] for m in rows
       if any((m.get("managed") or "").endswith(w) for w in want)]
gm = next((m for m in rows if m.get("scope_name") == "groups"), None)
if gm:
    pks.append(gm["pk"])
print("attach:", [m["name"].split(": ")[-1] for m in rows if m["pk"] in pks])

r = requests.patch(B + "/providers/oauth2/1/", headers=h,
                   json={"property_mappings": pks}, timeout=10)
pm = r.json().get("property_mappings", [])
print("patch:", r.status_code, "mappings:", [m if isinstance(m, str) else m.get("scope_name") for m in pm])
