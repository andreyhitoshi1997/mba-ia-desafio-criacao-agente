"""Adapter ADK para autorização de visitantes. Também no agente raiz (ADR-1)."""

from __future__ import annotations

import asyncio

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from aurora.aplicacao.consultas import meus_visitantes
from aurora.aplicacao.visitantes import executar_autorizacao
from aurora.dominio.visitantes import ComandoDeAutorizacao, TipoDeResultadoDaAutorizacao
from aurora.infra.repositorio import RepositorioSqlite

_repositorio = RepositorioSqlite()


async def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
    """Autoriza a entrada de um visitante para o apartamento da sessão atual.
    Libera acesso — SEMPRE pede confirmação, mesmo que o morador diga que já
    confirmou por texto (a confirmação vem só da rota dedicada).

    Args:
      nome: nome completo do visitante.
      data: data da visita, formato AAAA-MM-DD.
    """
    apartamento = tool_context.state["apartamento"]
    comando = ComandoDeAutorizacao(
        apartamento=apartamento,
        nome=nome,
        data=data,
        idem_key=str(tool_context.function_call_id),
    )
    resultado = await asyncio.to_thread(executar_autorizacao, _repositorio, comando)
    if resultado.tipo == TipoDeResultadoDaAutorizacao.JA_EXECUTADA:
        return {"status": "ja_autorizado", "nome": nome, "data": data}
    return {"status": "autorizado", "nome": nome, "data": data}


autorizar_visitante_tool = FunctionTool(autorizar_visitante, require_confirmation=True)


async def listar_meus_visitantes(tool_context: ToolContext) -> dict:
    """Lista os visitantes autorizados para o apartamento da sessão atual."""
    apartamento = tool_context.state["apartamento"]
    visitantes = await asyncio.to_thread(meus_visitantes, _repositorio, apartamento)
    return {
        "visitantes": [{"nome": v.nome, "data": v.data} for v in visitantes]
    }


listar_meus_visitantes_tool = FunctionTool(listar_meus_visitantes)
