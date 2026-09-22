"""Caso de uso: reservar uma área comum.

Não sabe nada de ADK, sqlite3 ou FastAPI — só conhece a porta
`RepositorioDeCondominio` e o domínio. É por isso que a Garantia 5 (exclusividade
sob concorrência) é testável com duas threads reais e sem Gemini: ver
`tests/test_concorrencia_reservas.py`.
"""

from __future__ import annotations

from aurora.aplicacao.portas import RepositorioDeCondominio
from aurora.dominio.areas import gera_cobranca
from aurora.dominio.reservas import ComandoDeReserva, ResultadoDaReserva


class AreaInexistente(Exception):
    pass


def area_gera_cobranca(repositorio: RepositorioDeCondominio, area: str) -> bool:
    """Usado como `require_confirmation` predicate pela tool ADK."""
    info = repositorio.buscar_area(area)
    if info is None:
        return False
    return gera_cobranca(info.taxa)


def executar_reserva(
    repositorio: RepositorioDeCondominio, comando: ComandoDeReserva
) -> ResultadoDaReserva:
    return repositorio.inserir_reserva(comando)
