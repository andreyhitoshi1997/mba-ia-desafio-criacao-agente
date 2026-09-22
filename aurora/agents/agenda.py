"""especialista_agenda (Garantia 2): único agente que consulta a agenda de
área comum. Devolve só disponibilidade booleana — nunca o dono da reserva.
Acionado pelo root via `AgentTool` (function call, não transferência), o que
roda numa sessão-filha efêmera e mantém qualquer dado alheio fora da sessão
principal.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool

from aurora.agents.resiliencia import RETRY_QUOTA_GEMINI
from aurora.tools.agenda import consultar_disponibilidade, listar_areas_comuns

MODEL = os.environ.get("AURORA_MODEL_AGENDA", os.environ.get("AURORA_MODEL", "gemini-2.5-flash"))

especialista_agenda = LlmAgent(
    name="especialista_agenda",
    model=MODEL,
    description=(
        "Consulta a agenda das áreas comuns (salão de festas, churrasqueira, "
        "quadra): se uma data está livre ou ocupada, e a lista de áreas com "
        "suas taxas. Nunca revela quem fez uma reserva."
    ),
    instruction=(
        "Você responde perguntas sobre disponibilidade de áreas comuns e "
        "sobre a lista de áreas com suas taxas, usando as tools disponíveis. "
        "Nunca invente disponibilidade: sempre chame a tool correspondente. "
        "Sua resposta nunca deve mencionar apartamento, morador ou código de "
        "reserva — apenas se a data está livre ou ocupada."
    ),
    tools=[
        FunctionTool(consultar_disponibilidade),
        FunctionTool(listar_areas_comuns),
    ],
    retry_config=RETRY_QUOTA_GEMINI,
)
