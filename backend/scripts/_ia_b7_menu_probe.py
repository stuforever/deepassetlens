# -*- coding: utf-8 -*-
"""批7 7.2：菜单注册表完整性探针（七组全键级+placeholder 清零+键唯一）。"""
import collections
import re

src = open("../frontend/src/config/navigation.tsx", encoding="utf-8").read()
groups = re.findall(r"key: '(expert_[^']+|[^']+)'", src)
menukeys = re.findall(r"menuKey: '([^']+)'", src)
placeholders = re.findall(r"placeholder: true", src)

print("组 key（前 8）:", groups[:8])
print("menuKey 总数:", len(menukeys))
print("placeholder 残留:", len(placeholders))
dups = [k for k, c in collections.Counter(menukeys).items() if c > 1]
print("menuKey 重复:", dups if dups else "无")

# expertPages 侧
ep = open("../frontend/src/config/expertPages.ts", encoding="utf-8").read()
ep_keys = re.findall(r"menuKey: '([^']+)'", ep)
print("expertPages 路由数:", len(ep_keys), "| 重复:", [k for k, c in collections.Counter(ep_keys).items() if c > 1] or "无")

# 菜单键 ⊆ expertPages 或静态路由（键级对照：菜单中 e:tutor* 键须有注册路由）
menu_e = [k for k in menukeys if k.startswith("e:")]
ep_set = set(ep_keys)
missing = [k for k in menu_e if k not in ep_set]
print("菜单 e:* 键无 expertPages 路由:", missing if missing else "无")
