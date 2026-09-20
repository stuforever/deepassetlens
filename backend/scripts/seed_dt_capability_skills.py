# -*- coding: utf-8 -*-
"""v3 批1：8 技能种子（技能面唯一注册表）——Skill+SkillVersion 幂等。
content=能力元数据（icon/allowedTools/defaultTools/loopEngine/configPanel——值源=fieldlists/skill-meta.md，
DT home page.tsx L217-290 CAPABILITIES + L192-201 ALL_TOOLS + L1385-1440 configPanel 挂载实证）。
input_schema：quiz/book-generate 字段级（spec §一表），其余 {}。
台账登记：Skill.status='published'（skill_manager L316 实证，计划模板 'released' 修正）；
SkillExecLog.created_via='agent'（模型 CheckConstraint 白名单，计划 'bridge' 违约修正）。"""
import sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.core.database import SessionLocal          # noqa: E402
from app.models.skill import Skill, SkillVersion    # noqa: E402

DISCARDED = ["geogebra_analysis", "paper_search", "imagegen", "videogen"]  # 裁定②舍弃（UI 置灰）

# (code, name, desc, input_schema, icon, allowedTools, defaultTools, loopEngine, configPanel)
# 值源=fieldlists/skill-meta.md（1.2 产物，源实值——allowedTools 含舍弃件为元数据忠实；
# 运行时白名单=TOOL_WHITELIST∩req.tools，UI 舍弃件置灰批3 落地）
SKILLS = [
    ("sishu/chat", "私塾先生·对话", "主循环：多轮对话+工具白名单+知识库检索注入+历史引用",
     {},
     "MessageSquare",
     ["brainstorm", "geogebra_analysis", "web_search", "code_execution", "reason", "paper_search", "imagegen", "videogen"],
     [], False, "none"),
    ("sishu/solve", "私塾先生·解题", "推理循环：思考→工具→验证→作答",
     {},
     "BrainCircuit",
     ["web_search", "code_execution", "reason"],
     ["web_search", "code_execution", "reason"], True, "none"),
    ("sishu/quiz", "私塾先生·出题", "计划器→结构化出题→自检→题卡事件；action=judge 判题回分；mode=mimic 试卷仿制",
     {"type": "object", "properties": {
         "mode": {"type": "string", "enum": ["custom", "mimic"], "default": "custom"},
         "question_types": {"type": "array", "items": {"type": "string"}},
         "per_type_counts": {"type": "object"},
         "difficulty": {"type": "string"},
         "language": {"type": "string"},
         "exam_pdf": {"type": "string", "description": "mimic 模式试卷 PDF 引用"}},
      "required": []},
     "PenLine",
     ["web_search", "code_execution"],
     ["web_search", "code_execution"], False, "quiz"),
    ("sishu/research", "私塾先生·深研", "子代理编排：大纲→分节→汇总+进度事件",
     {"type": "object", "properties": {"mode": {"type": "string"}, "depth": {"type": "string"}, "outline": {"type": "string"}}, "required": []},
     "Microscope",
     ["web_search", "paper_search", "code_execution"],
     ["web_search", "paper_search", "code_execution"], False, "research"),
    ("sishu/visualize", "私塾先生·可视化", "SandboxExecutor 代码生成（svg/chartjs/mermaid/html/manim）→产物事件",
     {"type": "object", "properties": {"render_mode": {"type": "string", "enum": ["svg", "chartjs", "mermaid", "html", "manim"]}, "quality": {"type": "string"}}, "required": []},
     "BarChart3",
     [], [], False, "visualize"),
    ("sishu/mastery", "私塾先生·精通之路", "loop 引擎+mastery 工具组（status/quiz/grade/assess/build）",
     {},
     "GraduationCap",
     ["web_search", "code_execution"],
     [], True, "none"),
    ("sishu/wrong-intake", "私塾先生·错题录入", "对话式结构化抽取→确认卡→写库",
     {},
     "BookMarked",
     [], [], True, "none"),
    ("sishu/book-generate", "私塾先生·建书", "建书管线：意图→书脊→逐页（块类型路由）→块再生；channel=bridge_sse",
     {"type": "object", "properties": {
         "user_intent": {"type": "string"},
         "chat_session_id": {"type": "string"},
         "chat_selections": {"type": "array", "items": {"type": "object"}},
         "notebook_refs": {"type": "array", "items": {"type": "string"}},
         "knowledge_bases": {"type": "array", "items": {"type": "string"}},
         "question_categories": {"type": "array", "items": {"type": "string"}},
         "question_entries": {"type": "array", "items": {"type": "object"}},
         "language": {"type": "string"}},
      "required": ["user_intent"]},
     "BookOpen",
     ["web_search", "reason"],
     ["web_search"], False, "none"),
]


def main():
    db = SessionLocal()
    created, skipped = 0, 0
    try:
        for code, name, desc, schema, icon, allowed, default, loop, panel in SKILLS:
            if db.query(Skill).filter(Skill.skill_code == code).first():
                print(f"[seed] {code} 已存在，跳过")
                skipped += 1
                continue
            sid, vid = str(uuid.uuid4()), str(uuid.uuid4())
            db.add(Skill(skill_id=sid, skill_code=code, name=name, description=desc,
                         skill_type="deepagent", status="published", current_version_id=vid,
                         tags=["tutor", "deepagent"]))
            db.add(SkillVersion(version_id=vid, skill_id=sid, version="1.0.0", status="active",
                                input_schema=schema, output_schema={"type": "object", "properties": {}},
                                content={"icon": icon, "allowedTools": allowed,
                                         "defaultTools": default, "loopEngine": loop,
                                         "configPanel": panel, "discardedTools": DISCARDED}))
            db.commit()
            print(f"[seed] {code} 已创建")
            created += 1
        print(f"[seed] 完成：新建 {created}，跳过 {skipped}，总数 {created + skipped}/8")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
