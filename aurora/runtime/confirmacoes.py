"""Garantia 1: `confirmacoes_pendentes` é estado DERIVADO dos eventos da
sessão — nunca uma tabela paralela. Validado no spike
(`spikes/confirm_spike/RESULTADO.md`): sem essa derivação rodando ANTES de
qualquer chamada ao Runner, um reenvio da mesma confirmação faz o ADK
reexecutar a tool (achado empírico, não teórico) — é essa checagem que
garante o 409 do contrato e o "nada é executado" real, não delegado ao
framework.
"""

from __future__ import annotations

from dataclasses import dataclass

from google.genai import types

NOME_CONFIRMACAO = "adk_request_confirmation"


@dataclass(frozen=True, slots=True)
class ConfirmacaoPendente:
    id: str
    acao: str
    detalhes: dict


def pendentes_da_sessao(eventos) -> dict[str, "types.FunctionCall"]:
    """Varre os eventos e devolve {id_da_confirmacao: function_call} para as
    confirmações ainda sem resposta. Um `function_response` com o mesmo id
    (seja `confirmed: true` ou `false`) remove a pendência — negar também
    "resolve" a pendência, sem executar nada."""
    pedidos: dict = {}
    respondidos: set[str] = set()
    for evento in eventos:
        for chamada in evento.get_function_calls():
            if chamada.name == NOME_CONFIRMACAO and chamada.id:
                pedidos[chamada.id] = chamada
        for resposta in evento.get_function_responses():
            if resposta.name == NOME_CONFIRMACAO and resposta.id:
                respondidos.add(resposta.id)
    return {id_: fc for id_, fc in pedidos.items() if id_ not in respondidos}


def listar_confirmacoes_pendentes(eventos) -> list[ConfirmacaoPendente]:
    pendentes = pendentes_da_sessao(eventos)
    resultado = []
    for id_confirmacao, chamada in pendentes.items():
        original = (chamada.args or {}).get("originalFunctionCall") or {}
        resultado.append(
            ConfirmacaoPendente(
                id=id_confirmacao,
                acao=original.get("name", ""),
                detalhes=dict(original.get("args") or {}),
            )
        )
    return resultado


def content_de_resposta_de_confirmacao(id_confirmacao: str, confirmado: bool) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=id_confirmacao,
                    name=NOME_CONFIRMACAO,
                    response={"confirmed": confirmado},
                )
            )
        ],
    )
