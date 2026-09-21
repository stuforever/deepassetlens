"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

BUILTIN_CAPABILITY_CLASSES: dict[str, str] = {
    "chat": "app.services.sishu_full.agents.chat.capability:ChatCapability",
    "deep_solve": "app.services.sishu_full.capabilities.solve.capability:DeepSolveCapability",
    "deep_question": "app.services.sishu_full.agents.question.capability:DeepQuestionCapability",
    "deep_research": "app.services.sishu_full.agents.research.capability:DeepResearchCapability",
    "math_animator": "app.services.sishu_full.agents.math_animator.capability:MathAnimatorCapability",
    "visualize": "app.services.sishu_full.agents.visualize.capability:VisualizeCapability",
    "mastery_path": "app.services.sishu_full.capabilities.mastery.capability:MasteryPathCapability",
    "wrong_intake": "app.services.sishu_full.capabilities.wrong_intake.capability:WrongIntakeCapability",
}
