"""Garantia 2, verificada no nível estrutural que o passo 15 do avaliador
audita: nenhuma tool que muta reserva/visitante expõe `apartamento` no
schema enviado ao modelo — o parâmetro simplesmente não existe para o LLM
preencher, com ou sem prompt injection."""

from __future__ import annotations

from aurora.tools.reservas import (
    cancelar_reserva_tool,
    listar_minhas_reservas_tool,
    reservar_area_tool,
)
from aurora.tools.visitantes import autorizar_visitante_tool, listar_meus_visitantes_tool

_PROIBIDOS = {"apartamento", "apto", "unidade", "morador"}


def _propriedades(tool) -> set[str]:
    declaracao = tool._get_declaration()
    schema = declaracao.parameters_json_schema or (
        declaracao.parameters.model_dump() if declaracao.parameters else {}
    )
    return set((schema or {}).get("properties", {}).keys())


def test_nenhuma_tool_de_mutacao_expoe_apartamento():
    for tool in (
        reservar_area_tool,
        cancelar_reserva_tool,
        autorizar_visitante_tool,
        listar_minhas_reservas_tool,
        listar_meus_visitantes_tool,
    ):
        propriedades = _propriedades(tool)
        invasoras = _PROIBIDOS & propriedades
        assert not invasoras, f"{tool.name} expõe {invasoras} ao modelo: {propriedades}"


def test_reservar_area_so_expoe_area_e_data():
    assert _propriedades(reservar_area_tool) == {"area", "data"}


def test_cancelar_reserva_so_expoe_area_e_data_nunca_codigo():
    # Por design: se a tool aceitasse `codigo`, o modelo precisaria
    # descobrir o código de uma reserva alheia para "tentar" cancelá-la.
    propriedades = _propriedades(cancelar_reserva_tool)
    assert propriedades == {"area", "data"}
    assert "codigo" not in propriedades
