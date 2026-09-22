"""LLM determinístico para o spike: dispensa GEMINI_API_KEY.

Decide a resposta olhando só o último Content do llm_request:
- se ainda não há function_response para a chamada da tool -> emite a FunctionCall.
- se já há -> emite um texto final.
Isso isola o mecanismo de retomada do Runner/SessionService de qualquer
variabilidade de um LLM real.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

TOOL_NAME = "acao_sensivel"


class FakeLlm(BaseLlm):
    model: str = "fake-llm"

    async def generate_content_async(
        self, llm_request, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        contents = llm_request.contents
        ja_respondeu = any(
            part.function_response is not None
            for content in contents
            for part in (content.parts or [])
            if content.role == "user"
        ) and any(
            part.function_response is not None
            and part.function_response.name == TOOL_NAME
            for content in contents
            for part in (content.parts or [])
        )
        chamou_tool = any(
            part.function_call is not None and part.function_call.name == TOOL_NAME
            for content in contents
            for part in (content.parts or [])
        )

        if chamou_tool and ja_respondeu:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="ação concluída")],
                )
            )
            return

        if not chamou_tool:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id="fc-call-1",
                                name=TOOL_NAME,
                                args={"valor": 42},
                            )
                        )
                    ],
                )
            )
            return

        # tool foi chamada mas ainda não há resposta de confirmação -> não deveria
        # acontecer no fluxo do spike; devolve texto neutro para não travar.
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text="aguardando")])
        )
