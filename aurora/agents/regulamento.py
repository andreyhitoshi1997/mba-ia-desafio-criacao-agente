"""especialista_regulamento (Garantia 4): único agente que lê texto do
regulamento. Devolve um capítulo por vez, nunca o documento inteiro. Roda em
sessão-filha de `AgentTool`: o texto do capítulo nunca chega aos eventos da
sessão principal, e o agente raiz não importa este módulo nem recebe o
regulamento nas instruções.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool

from aurora.agents.resiliencia import RETRY_QUOTA_GEMINI
from aurora.tools.capitulos import consultar_regulamento

MODEL = os.environ.get(
    "AURORA_MODEL_REGULAMENTO", os.environ.get("AURORA_MODEL", "gemini-2.5-flash")
)

especialista_regulamento = LlmAgent(
    name="especialista_regulamento",
    model=MODEL,
    description=(
        "Responde dúvidas sobre o regulamento interno do condomínio "
        "(horários de áreas comuns, regras de convivência, animais, "
        "garagem, mudanças, obras, lixo, penalidades etc.), consultando o "
        "capítulo relevante."
    ),
    instruction=(
        "Você responde dúvidas sobre o regulamento interno do condomínio. "
        "Sempre use a tool `consultar_regulamento` com um assunto (uma "
        "palavra-chave) para buscar o capítulo relevante antes de responder — "
        "nunca responda de memória. Depois de consultar, responda em no "
        "máximo duas frases, citando o artigo quando fizer sentido. Se o "
        "assunto não for encontrado, diga que não encontrou e não invente."
    ),
    tools=[FunctionTool(consultar_regulamento)],
    retry_config=RETRY_QUOTA_GEMINI,
)
