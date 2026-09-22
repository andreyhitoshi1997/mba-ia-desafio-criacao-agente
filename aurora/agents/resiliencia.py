"""Retry com backoff para chamadas ao Gemini.

Fora de escopo das 5 garantias, mas necessário na prática: o próprio
enunciado avisa que o fluxo do avaliador faz "algumas dezenas de chamadas"
ao modelo, e o tier gratuito do Google AI Studio pode ter um limite de RPM
bem mais apertado do que isso (observado: 5 req/min para `gemini-2.5-flash`
numa chave nova) — um 429 transitório não pode derrubar a conversa.

`RetryConfig` é nativo do ADK e envolve o nó inteiro do agente (incluindo a
chamada ao modelo), não só a tool — reaplicado a cada um dos três agentes.
"""

from __future__ import annotations

from google.adk.workflow import RetryConfig

RETRY_QUOTA_GEMINI = RetryConfig(
    max_attempts=8,
    initial_delay=5.0,
    max_delay=60.0,
    backoff_factor=1.8,
    jitter=0.3,
    exceptions=["_ResourceExhaustedError", "ServerError"],
)
