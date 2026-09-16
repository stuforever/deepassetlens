# -*- coding: utf-8 -*-
"""批12 R1：mcp_server.py 摘除教学工具族（L219-296：头注+imports+_tutor_user+11 @mcp.tool）。"""
import io

P = r"D:\gitcangku\deepassetlens\backend\app\mcp_server.py"
with io.open(P, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 校验边界：块头注（教学工具族）起；块尾=export_wrong_book 工具函数的 return 行（非 import 行）
start = next(i for i, l in enumerate(lines) if "教学工具族" in l) - 1  # 含上方分隔线
end = next(i for i, l in enumerate(lines) if l.startswith("    return _impl_export_wrong_book"))
assert "-----------" in lines[start], lines[start]
print(f"block: lines {start+1}..{end+1}")

note = (
    "# ---------------------------------------------------------------------------\n"
    "# ⑤R R1（批12）：先行版教学工具族退役移除（原九件+⑤补补 fsrs_due/fsrs_review，共 11 件）——\n"
    "# 能力由 vendor 复刻件承接（deeptutor learning 原生 practice_generator/exercise_selector/\n"
    "# grading + self_learning/learner_profile 路由族）；学习域数据落 PG learning_* 四表冻结（M00 登记）。\n"
    "# ---------------------------------------------------------------------------\n"
)

new = lines[:start] + [note] + lines[end + 1:]
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.writelines(new)
print(f"OK: {len(lines)} -> {len(new)} lines")
