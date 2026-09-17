# -*- coding: utf-8 -*-
"""重置三个默认账号密码（akadmin/student/student2）。"""
import requests

h = {"Authorization": "Bearer deepassetlens_bootstrap_token_2026"}
B = "http://localhost:9100/api/v3"

r = requests.post(B + "/core/users/6/set_password/", headers=h,
                  json={"password": "deepassetlens_admin"}, timeout=10)
print("set akadmin pw:", r.status_code)

users = requests.get(B + "/core/users/", headers=h,
                     params={"search": "student"}, timeout=10).json()["results"]
for u in users:
    if u["username"] in ("student", "student2"):
        r2 = requests.post(f"{B}/core/users/{u['pk']}/set_password/", headers=h,
                           json={"password": "Tupu_student_2026"}, timeout=10)
        print(f"set {u['username']} pw:", r2.status_code)
