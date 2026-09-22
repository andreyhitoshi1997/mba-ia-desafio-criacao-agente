from __future__ import annotations

from aurora.aplicacao.portas import RepositorioDeCondominio
from aurora.dominio.reservas import Reserva
from aurora.dominio.visitantes import Visitante


def minhas_reservas(repositorio: RepositorioDeCondominio, apartamento: str) -> list[Reserva]:
    return repositorio.listar_reservas_do_apartamento(apartamento)


def meus_visitantes(repositorio: RepositorioDeCondominio, apartamento: str) -> list[Visitante]:
    return repositorio.listar_visitantes_do_apartamento(apartamento)


def data_esta_livre(repositorio: RepositorioDeCondominio, area: str, data: str) -> bool:
    """Garantia 2: só devolve livre/ocupado — nunca revela de quem é a reserva."""
    return not repositorio.existe_reserva_ativa(area, data)


def areas_disponiveis(repositorio: RepositorioDeCondominio) -> list:
    return repositorio.listar_areas()
