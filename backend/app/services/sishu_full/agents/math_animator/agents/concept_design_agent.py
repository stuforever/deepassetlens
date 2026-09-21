"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json

from app.services.sishu_full.agents.base_agent import BaseAgent
from app.services.sishu_full.core.trace import build_trace_metadata, new_call_id

from ..models import ConceptAnalysis, SceneDesign
from ..utils import extract_json_object


class ConceptDesignAgent(BaseAgent):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        language: str = "zh",
    ) -> None:
        super().__init__(
            module_name="math_animator",
            agent_name="concept_design_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
        )

    async def process(
        self,
        *,
        user_input: str,
        output_mode: str,
        analysis: ConceptAnalysis,
        style_hint: str,
    ) -> SceneDesign:
        system_prompt = self.get_prompt("system")
        user_template = self.get_prompt("user_template")
        if not system_prompt or not user_template:
            raise ValueError("ConceptDesignAgent prompts are not configured.")

        user_prompt = user_template.format(
            user_input=user_input.strip(),
            output_mode=output_mode,
            style_hint=style_hint.strip() or "(none)",
            analysis_json=json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2),
        )
        _chunks: list[str] = []
        async for _c in self.stream_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            stage="concept_design",
            trace_meta=build_trace_metadata(
                call_id=new_call_id("math-design"),
                phase="concept_design",
                label="Concept design",
                call_kind="math_concept_design",
                trace_role="design",
                trace_kind="llm_output",
            ),
        ):
            _chunks.append(_c)
        response = "".join(_chunks)
        return SceneDesign.model_validate(extract_json_object(response))
