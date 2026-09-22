from __future__ import annotations

from aurora.aplicacao.portas import RepositorioDeCondominio
from aurora.dominio.visitantes import ComandoDeAutorizacao, ResultadoDaAutorizacao


def executar_autorizacao(
    repositorio: RepositorioDeCondominio, comando: ComandoDeAutorizacao
) -> ResultadoDaAutorizacao:
    return repositorio.inserir_visitante(comando)
