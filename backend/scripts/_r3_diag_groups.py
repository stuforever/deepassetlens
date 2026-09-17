# -*- coding: utf-8 -*-
"""诊断 akadmin 无 auth.write：JWT groups claim + provider property mappings。"""
import requests

h = {"Authorization": "Bearer deepassetlens_bootstrap_token_2026"}
B = "http://localhost:9100/api/v3"

p = requests.get(B + "/providers/oauth2/1/", headers=h, timeout=10).json()
print("property_mappings:", [m.get("name") for m in p.get("property_mappings", [])])
print("scopes:", p.get("scopes") if "scopes" in p else "-")

# 全部 oauth2 property mappings
maps = requests.get(B + "/propertymappings/provider/oauth2/", headers=h, timeout=10).json()
print("\nall oauth2 mappings:")
for m in maps.get("results", []):
    print(f"  {m['pk'][:8]} {m['name']} managed={m.get('managed')}")

# tupu-admin 组
groups = requests.get(B + "/core/groups/", headers=h, params={"search": "tupu"}, timeout=10).json()
print("\ngroups:")
for g in groups.get("results", []):
    users = [u.get("username") for u in g.get("users_obj", [])]
    print(f"  {g['pk'][:8]} {g['name']} users={users}")
