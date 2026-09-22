from __future__ import annotations

from aurora.aplicacao.portas import RepositorioDeCondominio
from aurora.dominio.reservas import ComandoDeCancelamento, ResultadoDoCancelamento


def executar_cancelamento(
    repositorio: RepositorioDeCondominio, comando: ComandoDeCancelamento
) -> ResultadoDoCancelamento:
    """Regra de negócio 4: cancela só reserva do PRÓPRIO apartamento — o
    `comando.apartamento` vem sempre da sessão (Garantia 2), nunca do texto do
    morador, então uma reserva de outro apartamento simplesmente não é
    encontrada pelo WHERE escopado no repositório."""
    return repositorio.cancelar_reserva(comando)
