"""Adapters ADK para as tools de reserva. Ficam no agente raiz (ADR-1/spike):
é o que garante que o Runner sempre encontra o autor certo ao retomar uma
confirmação, inclusive depois de um restart com sessão persistida.

Cada função aqui tem ~10 linhas e delega tudo para `aplicacao/` — nenhuma
regra de negócio mora neste arquivo.
"""

from __future__ import annotations

import asyncio

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from aurora.aplicacao.cancelar import executar_cancelamento
from aurora.aplicacao.consultas import minhas_reservas
from aurora.aplicacao.reservar import area_gera_cobranca, executar_reserva
from aurora.dominio.reservas import (
    ComandoDeCancelamento,
    ComandoDeReserva,
    TipoDeCancelamento,
    TipoDeResultado,
)
from aurora.infra.repositorio import RepositorioSqlite

_repositorio = RepositorioSqlite()


async def _area_requer_confirmacao(area: str, **_ignorado) -> bool:
    """Predicate de `require_confirmation`: recebe TODOS os args da tool
    original (area, data), por isso `**_ignorado` — sem ele, o ADK estoura
    TypeError e a chamada vira 500 (achado verificado no ADK 2.9.2)."""
    return await asyncio.to_thread(area_gera_cobranca, _repositorio, area)


async def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Reserva uma área comum para o apartamento da sessão atual.

    Args:
      area: id da área comum (ex.: "salao-de-festas", "churrasqueira", "quadra").
      data: data da reserva, formato AAAA-MM-DD.
    """
    apartamento = tool_context.state["apartamento"]
    comando = ComandoDeReserva(
        apartamento=apartamento,
        area=area,
        data=data,
        # function_call_id é estável entre a chamada original e qualquer
        # retomada de confirmação (validado no spike) — uuid4() não seria.
        idem_key=str(tool_context.function_call_id),
    )
    resultado = await asyncio.to_thread(executar_reserva, _repositorio, comando)
    if resultado.tipo == TipoDeResultado.AGENDA_OCUPADA:
        return {
            "status": "indisponivel",
            "mensagem": "Essa área já está reservada nessa data.",
        }
    if resultado.tipo == TipoDeResultado.JA_EXECUTADA:
        return {"status": "ja_reservada", "codigo": resultado.codigo}
    return {"status": "reservada", "codigo": resultado.codigo}


reservar_area_tool = FunctionTool(
    reservar_area, require_confirmation=_area_requer_confirmacao
)


async def cancelar_reserva(area: str, data: str, tool_context: ToolContext) -> dict:
    """Cancela a reserva do PRÓPRIO apartamento (da sessão atual) numa área e
    data. Nunca cancela reserva de outro apartamento — se não houver reserva
    sua nessa área/data, simplesmente não encontra nada para cancelar.

    Args:
      area: id da área comum.
      data: data da reserva, formato AAAA-MM-DD.
    """
    apartamento = tool_context.state["apartamento"]
    comando = ComandoDeCancelamento(apartamento=apartamento, area=area, data=data)
    resultado = await asyncio.to_thread(executar_cancelamento, _repositorio, comando)
    if resultado.tipo == TipoDeCancelamento.NAO_ENCONTRADA:
        return {"status": "nenhuma_reserva_sua"}
    return {"status": "cancelada", "codigo": resultado.codigo}


cancelar_reserva_tool = FunctionTool(cancelar_reserva)  # nunca pede confirmação


async def listar_minhas_reservas(tool_context: ToolContext) -> dict:
    """Lista as reservas ativas do apartamento da sessão atual."""
    apartamento = tool_context.state["apartamento"]
    reservas = await asyncio.to_thread(minhas_reservas, _repositorio, apartamento)
    return {
        "reservas": [
            {"codigo": r.codigo, "area": r.area, "data": r.data} for r in reservas
        ]
    }


listar_minhas_reservas_tool = FunctionTool(listar_minhas_reservas)
