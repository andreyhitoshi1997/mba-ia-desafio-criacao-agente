"""Regras puras sobre áreas comuns. Zero dependência de ADK/sqlite3/FastAPI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Area:
    id: str
    nome: str
    taxa: float


def gera_cobranca(taxa: float) -> bool:
    """Regra de negócio 2: taxa > 0 gera cobrança; taxa 0 não gera."""
    return taxa > 0
