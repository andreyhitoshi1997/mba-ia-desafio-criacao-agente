"""Garantia 5, testável sem Gemini: duas threads reais disputando a mesma
área/data — exatamente uma reserva ativa deve sobreviver, sem exceção
vazando (equivalente ao passo 14 do avaliador, no nível do repositório)."""

from __future__ import annotations

import threading

from aurora.dominio.reservas import ComandoDeReserva, TipoDeResultado
from aurora.infra.repositorio import RepositorioSqlite


def test_duas_threads_mesma_area_e_data_produzem_uma_unica_reserva_ativa(
    banco_de_negocio_limpo,
):
    repo = RepositorioSqlite()
    resultados: list = [None, None]
    erros: list = [None, None]

    def tentar(indice: int, apartamento: str) -> None:
        try:
            comando = ComandoDeReserva(
                apartamento=apartamento,
                area="salao-de-festas",
                data="2030-05-11",
                idem_key=f"disputa-{indice}",
            )
            resultados[indice] = repo.inserir_reserva(comando)
        except Exception as exc:  # nunca deveria vazar exceção (Garantia 5)
            erros[indice] = exc

    t1 = threading.Thread(target=tentar, args=(0, "101"))
    t2 = threading.Thread(target=tentar, args=(1, "201"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert erros == [None, None], f"nenhuma exceção deveria vazar: {erros}"

    tipos = [r.tipo for r in resultados]
    assert tipos.count(TipoDeResultado.CRIADA) == 1, tipos
    assert tipos.count(TipoDeResultado.AGENDA_OCUPADA) == 1, tipos

    ativas = repo.listar_reservas_do_apartamento("101") + repo.listar_reservas_do_apartamento(
        "201"
    )
    do_salao_na_data = [r for r in ativas if r.area == "salao-de-festas" and r.data == "2030-05-11"]
    assert len(do_salao_na_data) == 1, do_salao_na_data


def test_vinte_rodadas_de_disputa_nunca_duplicam(banco_de_negocio_limpo):
    """Estresse estatístico: intermitência de race condition não deve passar
    "por sorte" numa única execução."""
    repo = RepositorioSqlite()
    for rodada in range(20):
        data = f"2031-01-{rodada + 1:02d}"
        resultados: list = [None, None]

        def tentar(indice: int) -> None:
            comando = ComandoDeReserva(
                apartamento="101",
                area="quadra" if rodada % 2 == 0 else "salao-de-festas",
                data=data,
                idem_key=f"rodada-{rodada}-{indice}",
            )
            resultados[indice] = repo.inserir_reserva(comando)

        threads = [threading.Thread(target=tentar, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        tipos = [r.tipo for r in resultados]
        assert tipos.count(TipoDeResultado.CRIADA) == 1, (rodada, tipos)
