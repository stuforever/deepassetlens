# -*- coding: utf-8 -*-
"""核对 akadmin pk 与同邮箱用户冲突。"""
import requests

h = {"Authorization": "Bearer deepassetlens_bootstrap_token_2026"}
B = "http://localhost:9100/api/v3"

r = requests.get(B + "/core/users/", headers=h, timeout=10).json()
for u in r["results"]:
    print(f"pk={u['pk']:>3} {u['username']:<12} email={u.get('email') or '-':<32} type={u.get('type')} active={u.get('is_active')}")
