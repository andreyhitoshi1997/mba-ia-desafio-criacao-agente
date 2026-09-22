"""Modelo de domínio de reservas. Zero dependência de ADK/sqlite3/FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


@dataclass(frozen=True, slots=True)
class Reserva:
    codigo: str
    apartamento: str
    area: str
    data: str  # AAAA-MM-DD
    status: str  # "ativa" | "cancelada"


@dataclass(frozen=True, slots=True)
class ComandoDeReserva:
    apartamento: str
    area: str
    data: str
    idem_key: str


class TipoDeResultado(Enum):
    CRIADA = auto()
    JA_EXECUTADA = auto()
    AGENDA_OCUPADA = auto()


@dataclass(frozen=True, slots=True)
class ResultadoDaReserva:
    tipo: TipoDeResultado
    codigo: str | None = None

    @classmethod
    def criada(cls, codigo: str) -> "ResultadoDaReserva":
        return cls(tipo=TipoDeResultado.CRIADA, codigo=codigo)

    @classmethod
    def ja_executada(cls, codigo: str) -> "ResultadoDaReserva":
        return cls(tipo=TipoDeResultado.JA_EXECUTADA, codigo=codigo)

    @classmethod
    def agenda_ocupada(cls) -> "ResultadoDaReserva":
        return cls(tipo=TipoDeResultado.AGENDA_OCUPADA)


@dataclass(frozen=True, slots=True)
class ComandoDeCancelamento:
    apartamento: str
    area: str
    data: str


class TipoDeCancelamento(Enum):
    CANCELADA = auto()
    NAO_ENCONTRADA = auto()


@dataclass(frozen=True, slots=True)
class ResultadoDoCancelamento:
    tipo: TipoDeCancelamento
    codigo: str | None = None
