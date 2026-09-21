"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
from typing import Any

from ..models import BlockType, SourceAnchor
from .base import BlockContext, BlockGenerator, GenerationFailure

logger = logging.getLogger(__name__)


def _starter_review_html() -> str:
    """Return a deterministic, source-locked review for Starter Modules 1-4."""
    questions = [
        ("M1 U1", "Miss Zhou: Good morning, class.  Class: _____.", ["Good afternoon, Miss Zhou.", "Good morning, Miss Zhou.", "Goodbye, Miss Zhou.", "Hello, Tony."], 1, "S2-S3"),
        ("M1 U1", "Which expression is used for the afternoon greeting?", ["Good morning.", "Good afternoon.", "Goodbye.", "How are you?"], 1, "S2-S3"),
        ("M1 U1", "Which item belongs to the ABC activity in the textbook?", ["ABC Song", "Weather map", "Telephone numbers", "Favourite sports"], 0, "S2-S3"),
        ("M1 U2", "What is the correct question for asking a person's name?", ["How old are you?", "What's your name, please?", "What's the weather like?", "What colour is it?"], 1, "S4-S5"),
        ("M1 U2", "How does Lingling politely ask Chen Zhong to spell her name?", ["Can you help me, please?", "Can you spell it, please?", "Can you say that again, please?", "How are you?"], 1, "S4-S5"),
        ("M2 U1", "The teacher says: Open your book. What should you do?", ["合上书", "打开书", "起立", "举手"], 1, "S8-S9"),
        ("M2 U1", "Which is the textbook instruction for raising your hand?", ["Stand up.", "Sit down.", "Put up your hand.", "Close your book."], 2, "S8-S9"),
        ("M2 U2", "Which number is spelled seven?", ["6", "7", "8", "9"], 1, "S10-S11"),
        ("M2 U2", "In the textbook, 'What's your number?' asks about a student's _____.", ["age", "favourite sport", "number", "colour"], 2, "S10-S11"),
        ("M2 U3", "A: How old are you?  B: _____.", ["I'm in Class 3.", "I'm twelve.", "It's Tuesday.", "It's red."], 1, "S12-S13"),
        ("M2 U3", "Which word means 15?", ["fourteen", "fifteen", "sixteen", "seventeen"], 1, "S12-S13"),
        ("M2 U3", "The Unit 3 number practice includes simple _____.", ["sums", "weather reports", "sports matches", "alphabet songs"], 0, "S12-S13"),
        ("M3 U1", "A: What's this in English?  B: _____.", ["It's a book.", "It's Monday.", "I'm twelve.", "It's cold."], 0, "S14-S15"),
        ("M3 U1", "How do you spell pencil?", ["P-E-N-C-I-L", "P-E-N-S-I-L", "P-E-N-C-E-L", "P-E-N"], 0, "S14-S15"),
        ("M3 U2", "A: Can you help me, please?  B: _____.", ["Yes, of course.", "It's black.", "I'm twelve.", "Good afternoon."], 0, "S16-S17"),
        ("M3 U2", "After not hearing the spelling clearly, the textbook uses which sentence?", ["What colour is it?", "Can you say that again, please?", "What's your number?", "How old are you?"], 1, "S16-S17"),
        ("M3 U3", "A: What colour is it?  B: _____.", ["It's black.", "It's a book.", "It's Tuesday.", "I'm Chen Zhong."], 0, "S18-S19"),
        ("M4 U1", "A: What day is it today?  B: _____.", ["It's Monday.", "It's spring.", "It's football.", "It's warm."], 0, "S20-S21"),
        ("M4 U2", "What is the weather like in winter in the textbook?", ["It's hot.", "It's warm.", "It's cool.", "It's cold."], 3, "S22-S23"),
        ("M4 U3", "A: What's your favourite sport?  B: _____.", ["Football.", "Monday.", "Brown.", "Twelve."], 0, "S24-S25"),
    ]
    import json
    data = json.dumps(
        [{"module": m, "prompt": q, "options": opts, "answer": answer, "source": source} for m, q, opts, answer, source in questions],
        ensure_ascii=False,
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{color-scheme:light;--ink:#172033;--muted:#64748b;--line:#dbe3ef;--brand:#2563eb;--ok:#15803d;--bad:#b91c1c}}
*{{box-sizing:border-box}}body{{margin:0;padding:18px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:#f8fafc}}
.wrap{{max-width:720px;margin:auto;background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px;box-shadow:0 5px 18px #0f172a12}}
.top{{display:flex;justify-content:space-between;gap:12px;align-items:start}}h2{{margin:0 0 6px;font-size:20px}}.muted{{color:var(--muted);font-size:13px}}
.bar{{height:7px;background:#e8eef7;border-radius:8px;overflow:hidden;margin:16px 0 20px}}.bar i{{display:block;height:100%;background:var(--brand);width:5%;transition:width .2s}}
.tag{{color:var(--brand);font-size:13px;font-weight:650}}.q{{font-size:18px;line-height:1.55;margin:12px 0 16px;white-space:pre-wrap}}
.opts{{display:grid;gap:10px}}button{{font:inherit;cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:8px;padding:11px 13px;text-align:left;transition:.15s}}
button:hover{{border-color:var(--brand);background:#eff6ff}}button:disabled{{cursor:default}}button.correct{{border-color:#86efac;background:#f0fdf4;color:var(--ok)}}button.wrong{{border-color:#fecaca;background:#fef2f2;color:var(--bad)}}
.feedback{{min-height:25px;margin:14px 0 4px;font-size:14px;font-weight:600}}.feedback.ok{{color:var(--ok)}}.feedback.bad{{color:var(--bad)}}
.foot{{display:flex;justify-content:space-between;align-items:center;margin-top:16px}}.next{{background:var(--brand);color:#fff;border-color:var(--brand);text-align:center;padding:9px 18px}}.next:disabled{{opacity:.45}}
.result{{text-align:center;padding:22px 5px}}.result strong{{font-size:34px;color:var(--brand);display:block;margin:10px}}
</style></head><body><main class="wrap"><div class="top"><div><h2>Starter Module 1–4 课本核对练习</h2><div class="muted">20 道动态选择题，按原教材 S2–S25 编排</div></div><div class="tag" id="count">1 / 20</div></div><div class="bar"><i id="progress"></i></div><section id="quiz"></section></main>
<script>
const qs={data};let index=0,score=0,answered=false;
const root=document.getElementById('quiz'),count=document.getElementById('count'),progress=document.getElementById('progress');
function render(){{answered=false;const x=qs[index];count.textContent=`${{index+1}} / ${{qs.length}}`;progress.style.width=`${{(index+1)/qs.length*100}}%`;root.innerHTML=`<div class="tag">${{x.module}} · 原教材 ${{x.source}}</div><div class="q">${{x.prompt}}</div><div class="opts">${{x.options.map((o,i)=>`<button data-i="${{i}}">${{String.fromCharCode(65+i)}}. ${{o}}</button>`).join('')}}</div><div class="feedback" id="feedback"></div><div class="foot"><span class="muted">答对后可进入下一题</span><button class="next" id="next" disabled>${{index===qs.length-1?'查看结果':'下一题'}}</button></div>`;document.querySelectorAll('.opts button').forEach(b=>b.onclick=()=>answer(+b.dataset.i));document.getElementById('next').onclick=()=>{{if(index<qs.length-1){{index++;render()}}else result()}}}}
function answer(i){{if(answered)return;answered=true;const x=qs[index],buttons=[...document.querySelectorAll('.opts button')];buttons.forEach(b=>b.disabled=true);buttons[x.answer].classList.add('correct');const f=document.getElementById('feedback');if(i===x.answer){{score++;f.textContent='回答正确';f.className='feedback ok'}}else{{buttons[i].classList.add('wrong');f.textContent=`再看一眼教材：正确答案是 ${{String.fromCharCode(65+x.answer)}}`;f.className='feedback bad'}}document.getElementById('next').disabled=false}}
function result(){{root.innerHTML=`<div class="result"><div class="tag">Starter Module 1–4</div><strong>${{score}} / ${{qs.length}}</strong><div>${{score===qs.length?'全部正确，教材核对得很扎实。':score>=15?'整体掌握不错，错题回到对应 S 页再读一遍。':'建议按页面标注的 S 页回读原对话，再重新练习。'}}</div><div class="foot"><span class="muted">练习已完成</span><button class="next" onclick="index=0;score=0;render()">重新练习</button></div></div>`;count.textContent='完成';progress.style.width='100%'}}render();
</script></body></html>'''


class InteractiveGenerator(BlockGenerator):
    block_type = BlockType.INTERACTIVE

    async def _generate(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        params = ctx.block.params
        if params.get("starter_review_20"):
            return (
                {
                    "render_type": "html",
                    "code": {"language": "html", "content": _starter_review_html()},
                    "description": "按外研社英语七年级上册 Starter Module 1-4 原教材 S2-S25 编排的 20 道动态选择题。",
                    "chart_type": "quiz",
                },
                [],
                {
                    "review_changed": False,
                    "review_notes": "Deterministic source-locked Starter review.",
                },
            )
        chapter_title = params.get("chapter_title", ctx.chapter.title)
        chapter_summary = params.get("chapter_summary", ctx.chapter.summary)
        objectives = params.get("objectives") or ctx.chapter.learning_objectives
        focus = str(params.get("focus") or "")
        interaction = str(params.get("interaction") or "interactive")

        history_lines: list[str] = []
        if chapter_summary:
            history_lines.append(f"Chapter summary: {chapter_summary}")
        if objectives:
            history_lines.append("Learning objectives:")
            for obj in objectives:
                history_lines.append(f"- {obj}")
        history_context = "\n".join(history_lines)

        focus_clause = f" focusing on {focus}" if focus else ""
        user_input = (
            f"Build an {interaction} HTML page for the chapter "
            f'"{chapter_title}"{focus_clause}. The page should let the learner '
            "manipulate state, drag/click controls, or step through a guided "
            "demo to internalise the concept."
        )

        try:
            from app.services.sishu_full.agents.visualize.pipeline import VisualizePipeline
            from app.services.sishu_full.agents.visualize.utils import validate_visualization
            from app.services.sishu_full.services.llm.config import get_llm_config

            llm_config = get_llm_config()
            pipeline = VisualizePipeline(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                api_version=llm_config.api_version,
                language=ctx.language,
            )
            analysis = await pipeline.run_analysis(
                user_input=user_input,
                history_context=history_context,
                render_mode="html",
            )
            code = await pipeline.run_code_generation(
                user_input=user_input,
                history_context=history_context,
                analysis=analysis,
            )
        except Exception as exc:
            logger.warning(f"InteractiveGenerator failed: {exc}", exc_info=True)
            raise GenerationFailure(f"interactive generation failed: {exc}") from exc

        ok, validation_error = validate_visualization(code, "html")
        if not ok:
            raise GenerationFailure(f"interactive html failed validation: {validation_error}")

        return (
            {
                "render_type": "html",
                "code": {"language": "html", "content": code},
                "description": analysis.description,
                "chart_type": analysis.chart_type,
            },
            [],
            {
                "review_changed": False,
                "review_notes": "Passed local validation.",
            },
        )


__all__ = ["InteractiveGenerator"]
