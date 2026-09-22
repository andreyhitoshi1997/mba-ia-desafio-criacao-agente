"""Derivação de confirmações pendentes a partir dos eventos da sessão (ADR-5).

Versão de spike, idêntica em espírito à que vai para
src/aurora/runtime/confirmacoes.py — validada aqui antes de virar código de
produto.
"""

from __future__ import annotations

NOME_CONFIRMACAO = "adk_request_confirmation"


def pendentes_da_sessao(eventos) -> dict:
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
