"""Porta (Protocol) que a camada de aplicação depende e a infra implementa.

Zero dependência de ADK/FastAPI. `sqlite3` só existe do lado da implementação
em `infra/`, nunca aqui — é o que torna `aplicacao/` testável com um fake em
memória, sem banco, e o que torna o Plano C do ADR-8 (executar a ação
diretamente em Python, fora do loop do modelo) uma chamada de função, não uma
reescrita.
"""

from __future__ import annotations

from typing import Protocol

from aurora.dominio.areas import Area
from aurora.dominio.reservas import (
    ComandoDeCancelamento,
    ComandoDeReserva,
    Reserva,
    ResultadoDaReserva,
    ResultadoDoCancelamento,
)
from aurora.dominio.visitantes import ComandoDeAutorizacao, ResultadoDaAutorizacao, Visitante


class RepositorioDeCondominio(Protocol):
    def buscar_area(self, area_id: str) -> Area | None: ...

    def listar_areas(self) -> list[Area]: ...

    def inserir_reserva(self, comando: ComandoDeReserva) -> ResultadoDaReserva: ...

    def cancelar_reserva(self, comando: ComandoDeCancelamento) -> ResultadoDoCancelamento: ...

    def listar_reservas_do_apartamento(self, apartamento: str) -> list[Reserva]: ...

    def existe_reserva_ativa(self, area: str, data: str) -> bool: ...

    def inserir_visitante(
        self, comando: ComandoDeAutorizacao
    ) -> ResultadoDaAutorizacao: ...

    def listar_visitantes_do_apartamento(self, apartamento: str) -> list[Visitante]: ...
