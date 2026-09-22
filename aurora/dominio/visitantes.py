"""Modelo de domínio de autorizações de visitante. Zero dependência de ADK/sqlite3/FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


@dataclass(frozen=True, slots=True)
class Visitante:
    apartamento: str
    nome: str
    data: str  # AAAA-MM-DD


@dataclass(frozen=True, slots=True)
class ComandoDeAutorizacao:
    apartamento: str
    nome: str
    data: str
    idem_key: str


class TipoDeResultadoDaAutorizacao(Enum):
    CRIADA = auto()
    JA_EXECUTADA = auto()


@dataclass(frozen=True, slots=True)
class ResultadoDaAutorizacao:
    tipo: TipoDeResultadoDaAutorizacao
