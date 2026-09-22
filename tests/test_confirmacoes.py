"""Garantia 1, no nível de derivação de eventos — a peça validada no spike.
Constrói eventos ADK "à mão" (sem LLM) para testar `pendentes_da_sessao` nos
casos do enunciado: pendente, respondida (aprovada/negada) e reenvio."""

from __future__ import annotations

from google.adk.events.event import Event
from google.genai import types

from aurora.runtime.confirmacoes import listar_confirmacoes_pendentes, pendentes_da_sessao


def _evento_function_call(autor: str, nome: str, id_: str, args: dict) -> Event:
    return Event(
        author=autor,
        content=types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(id=id_, name=nome, args=args))],
        ),
    )


def _evento_function_response(autor: str, role: str, nome: str, id_: str, response: dict) -> Event:
    return Event(
        author=autor,
        content=types.Content(
            role=role,
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(id=id_, name=nome, response=response)
                )
            ],
        ),
    )


def test_confirmacao_sem_resposta_fica_pendente():
    eventos = [
        _evento_function_call("assistente_aurora", "reservar_area", "F1", {"area": "salao-de-festas", "data": "2030-04-20"}),
        _evento_function_call(
            "assistente_aurora",
            "adk_request_confirmation",
            "C1",
            {"originalFunctionCall": {"id": "F1", "name": "reservar_area", "args": {"area": "salao-de-festas", "data": "2030-04-20"}}},
        ),
    ]
    pendentes = pendentes_da_sessao(eventos)
    assert set(pendentes.keys()) == {"C1"}

    detalhadas = listar_confirmacoes_pendentes(eventos)
    assert len(detalhadas) == 1
    assert detalhadas[0].acao == "reservar_area"
    assert detalhadas[0].detalhes == {"area": "salao-de-festas", "data": "2030-04-20"}


def test_confirmacao_respondida_sai_das_pendentes():
    eventos = [
        _evento_function_call("assistente_aurora", "reservar_area", "F1", {"area": "quadra", "data": "2030-04-20"}),
        _evento_function_call(
            "assistente_aurora",
            "adk_request_confirmation",
            "C1",
            {"originalFunctionCall": {"id": "F1", "name": "reservar_area", "args": {}}},
        ),
        _evento_function_response("assistente_aurora", "user", "adk_request_confirmation", "C1", {"confirmed": True}),
    ]
    assert pendentes_da_sessao(eventos) == {}


def test_negar_tambem_sai_das_pendentes_sem_reexecutar():
    eventos = [
        _evento_function_call("assistente_aurora", "reservar_area", "F1", {}),
        _evento_function_call(
            "assistente_aurora", "adk_request_confirmation", "C1",
            {"originalFunctionCall": {"id": "F1", "name": "reservar_area", "args": {}}},
        ),
        _evento_function_response("assistente_aurora", "user", "adk_request_confirmation", "C1", {"confirmed": False}),
    ]
    assert pendentes_da_sessao(eventos) == {}


def test_reenvio_do_mesmo_id_nao_volta_a_ficar_pendente():
    """Reproduz o cenário do passo 8: reenviar a resposta de uma confirmação
    já respondida não pode fazer a API tratar como pendente de novo — é isso
    que garante o 409 sem tocar o Runner."""
    eventos = [
        _evento_function_call("assistente_aurora", "reservar_area", "F1", {}),
        _evento_function_call(
            "assistente_aurora", "adk_request_confirmation", "C1",
            {"originalFunctionCall": {"id": "F1", "name": "reservar_area", "args": {}}},
        ),
        _evento_function_response("assistente_aurora", "user", "adk_request_confirmation", "C1", {"confirmed": True}),
        _evento_function_response("assistente_aurora", "user", "reservar_area", "F1", {"status": "reservada"}),
    ]
    # Um segundo POST /confirmacoes com o mesmo id=C1 checa isto ANTES do
    # Runner: C1 não está mais pendente -> a rota devolve 409 direto.
    assert "C1" not in pendentes_da_sessao(eventos)
