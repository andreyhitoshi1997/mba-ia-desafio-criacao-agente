"""Tools do especialista_agenda (Garantia 2): o único caminho de código que
lê a agenda de área comum, e devolve só {"disponivel": bool} — nunca o dono
da reserva. Roda numa sessão-filha de `AgentTool`, então mesmo que o texto
"quem reservou" aparecesse em algum lugar, não chegaria à sessão principal.
"""

from __future__ import annotations

import asyncio

from aurora.aplicacao.consultas import areas_disponiveis, data_esta_livre
from aurora.infra.repositorio import RepositorioSqlite

_repositorio = RepositorioSqlite()


async def consultar_disponibilidade(area: str, data: str) -> dict:
    """Verifica se uma área comum está livre numa data. Devolve só se está
    livre ou ocupada — nunca revela de quem é a reserva.

    Args:
      area: id da área comum.
      data: data a checar, formato AAAA-MM-DD.
    """
    livre = await asyncio.to_thread(data_esta_livre, _repositorio, area, data)
    return {"disponivel": livre}


async def listar_areas_comuns() -> dict:
    """Lista as áreas comuns do condomínio, com id, nome e taxa."""
    areas = await asyncio.to_thread(areas_disponiveis, _repositorio)
    return {"areas": [{"id": a.id, "nome": a.nome, "taxa": a.taxa} for a in areas]}
