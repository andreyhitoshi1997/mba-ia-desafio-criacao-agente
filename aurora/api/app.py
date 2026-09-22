"""API HTTP do assistente do Residencial Aurora — contrato exato do enunciado.

O gate de confirmação (409) roda ANTES de qualquer chamada ao Runner
(Garantia 1, validado no spike): `POST /confirmacoes` deriva as pendências da
sessão e só invoca o modelo se o id pedido estiver de fato pendente.

O apartamento da sessão é gravado uma única vez, no state, na criação —
nunca lido do texto do morador (Garantia 2): ver `POST /sessoes` abaixo.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from google.genai import types

from aurora.api.schemas import (
    ConfirmacaoPendenteResponse,
    CriarSessaoRequest,
    CriarSessaoResponse,
    MensagemRequest,
    ReservaResponse,
    ResponderConfirmacaoRequest,
    RespostaDaConversa,
    VisitanteResponse,
)
from aurora.infra.repositorio import RepositorioSqlite
from aurora.runtime.adk import APP_NAME, USER_ID, app as adk_app, obter_runner, obter_session_service
from aurora.runtime.confirmacoes import (
    content_de_resposta_de_confirmacao,
    listar_confirmacoes_pendentes,
    pendentes_da_sessao,
)

logger = logging.getLogger("aurora.api")

api = FastAPI(title="Assistente do Residencial Aurora")

_repositorio = RepositorioSqlite()

_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


async def _lock_da_sessao(session_id: str) -> asyncio.Lock:
    async with _locks_guard:
        lock = _locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _locks[session_id] = lock
        return lock


def _texto_da_resposta(eventos_da_invocacao: list) -> str:
    partes = []
    for evento in eventos_da_invocacao:
        if evento.author != adk_app.root_agent.name or not evento.content:
            continue
        for parte in evento.content.parts or []:
            if parte.text:
                partes.append(parte.text)
    return "".join(partes)


async def _rodar_e_montar_resposta(session_id: str, mensagem: types.Content) -> RespostaDaConversa:
    runner = obter_runner()
    lock = await _lock_da_sessao(session_id)
    async with lock:
        eventos_da_invocacao = [
            evento
            async for evento in runner.run_async(
                user_id=USER_ID, session_id=session_id, new_message=mensagem
            )
        ]

    sessao = await obter_session_service().get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    pendentes = listar_confirmacoes_pendentes(sessao.events)
    return RespostaDaConversa(
        resposta=_texto_da_resposta(eventos_da_invocacao),
        confirmacoes_pendentes=[
            ConfirmacaoPendenteResponse(id=p.id, acao=p.acao, detalhes=p.detalhes)
            for p in pendentes
        ],
    )


@api.post("/sessoes", status_code=201)
async def criar_sessao(corpo: CriarSessaoRequest) -> CriarSessaoResponse:
    sessao = await obter_session_service().create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        # Garantia 2: o apartamento é gravado aqui, uma única vez, no state
        # da sessão gerenciado pelo ADK — as tools leem daqui
        # (tool_context.state["apartamento"]), nunca de um argumento que o
        # modelo preenche a partir do texto do morador.
        state={"apartamento": corpo.apartamento},
    )
    return CriarSessaoResponse(session_id=sessao.id)


@api.post("/sessoes/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, corpo: MensagemRequest) -> RespostaDaConversa:
    sessao = await obter_session_service().get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if sessao is None:
        raise HTTPException(status_code=404, detail="sessão não encontrada")

    mensagem = types.Content(role="user", parts=[types.Part(text=corpo.texto)])
    return await _rodar_e_montar_resposta(session_id, mensagem)


@api.post("/sessoes/{session_id}/confirmacoes")
async def responder_confirmacao(
    session_id: str, corpo: ResponderConfirmacaoRequest
) -> RespostaDaConversa:
    sessao = await obter_session_service().get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if sessao is None:
        raise HTTPException(status_code=404, detail="sessão não encontrada")

    # Gate pré-Runner (Garantia 1): decide o 409 SEM tocar o Runner. Cobre
    # id inexistente e id já respondido (reenvio) — nos dois casos, nada é
    # executado, porque o Runner nem chega a ser chamado.
    pendentes = pendentes_da_sessao(sessao.events)
    if corpo.id not in pendentes:
        raise HTTPException(status_code=409, detail="confirmação não está pendente nesta sessão")

    mensagem = content_de_resposta_de_confirmacao(corpo.id, corpo.confirmado)
    resposta = await _rodar_e_montar_resposta(session_id, mensagem)

    sessao_apos = await obter_session_service().get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    ainda_pendente = corpo.id in pendentes_da_sessao(sessao_apos.events)
    if ainda_pendente:
        logger.error(
            "confirmacao_nao_retomada session_id=%s id=%s — a resposta não "
            "chegou ao agente que pediu a confirmação.",
            session_id,
            corpo.id,
        )
    return resposta


@api.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str) -> list[dict]:
    sessao = await obter_session_service().get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if sessao is None:
        raise HTTPException(status_code=404, detail="sessão não encontrada")
    return [evento.model_dump(mode="json", exclude_none=True) for evento in sessao.events]


@api.get("/apartamentos/{numero}/reservas")
async def reservas_do_apartamento(numero: str) -> list[ReservaResponse]:
    reservas = await asyncio.to_thread(
        _repositorio.listar_reservas_do_apartamento, numero
    )
    return [ReservaResponse(codigo=r.codigo, area=r.area, data=r.data) for r in reservas]


@api.get("/apartamentos/{numero}/visitantes")
async def visitantes_do_apartamento(numero: str) -> list[VisitanteResponse]:
    visitantes = await asyncio.to_thread(
        _repositorio.listar_visitantes_do_apartamento, numero
    )
    return [VisitanteResponse(nome=v.nome, data=v.data) for v in visitantes]
