"""Garantia 1, testável sem Gemini: reenviar o mesmo idem_key (equivalente a
`function_call_id`, achado do spike) nunca duplica — devolve a reserva já
criada. Regra de negócio 5: cancelamento nunca libera o código."""

from __future__ import annotations

from aurora.dominio.reservas import (
    ComandoDeCancelamento,
    ComandoDeReserva,
    TipoDeCancelamento,
    TipoDeResultado,
)
from aurora.infra.repositorio import RepositorioSqlite


def test_replay_da_mesma_idem_key_nao_duplica(banco_de_negocio_limpo):
    repo = RepositorioSqlite()
    comando = ComandoDeReserva(
        apartamento="101", area="salao-de-festas", data="2030-04-20", idem_key="fc-1"
    )

    primeiro = repo.inserir_reserva(comando)
    segundo = repo.inserir_reserva(comando)  # replay: mesmo idem_key

    assert primeiro.tipo == TipoDeResultado.CRIADA
    assert segundo.tipo == TipoDeResultado.JA_EXECUTADA
    assert segundo.codigo == primeiro.codigo

    reservas = repo.listar_reservas_do_apartamento("101")
    assert len(reservas) == 1


def test_negar_nao_grava_nada(banco_de_negocio_limpo):
    repo = RepositorioSqlite()
    # Negar significa nunca chamar inserir_reserva — este teste documenta a
    # invariante do lado do repositório: sem chamada, sem efeito.
    assert repo.listar_reservas_do_apartamento("101") == []


def test_cancelamento_e_soft_delete_codigo_nunca_reaparece(banco_de_negocio_limpo):
    repo = RepositorioSqlite()
    comando = ComandoDeReserva(
        apartamento="101", area="quadra", data="2030-03-09", idem_key="fc-2"
    )
    criada = repo.inserir_reserva(comando)
    codigo_original = criada.codigo

    resultado = repo.cancelar_reserva(
        ComandoDeCancelamento(apartamento="101", area="quadra", data="2030-03-09")
    )
    assert resultado.tipo == TipoDeCancelamento.CANCELADA
    assert resultado.codigo == codigo_original
    assert repo.listar_reservas_do_apartamento("101") == []

    # a data libera para nova reserva, mas o código antigo nunca reaparece
    nova = repo.inserir_reserva(
        ComandoDeReserva(apartamento="201", area="quadra", data="2030-03-09", idem_key="fc-3")
    )
    assert nova.tipo == TipoDeResultado.CRIADA
    assert nova.codigo != codigo_original


def test_cancelar_reserva_de_outro_apartamento_nao_encontra_nada(banco_de_negocio_limpo):
    repo = RepositorioSqlite()
    repo.inserir_reserva(
        ComandoDeReserva(apartamento="201", area="salao-de-festas", data="2030-03-16", idem_key="fc-4")
    )

    resultado = repo.cancelar_reserva(
        ComandoDeCancelamento(apartamento="101", area="salao-de-festas", data="2030-03-16")
    )
    assert resultado.tipo == TipoDeCancelamento.NAO_ENCONTRADA
    # a reserva do 201 continua intacta
    assert len(repo.listar_reservas_do_apartamento("201")) == 1
