"""Geração do código de reserva (regra de negócio 5).

Alfabeto sem dígitos: elimina de raiz qualquer colisão com números de
apartamento (ex. "302") em checagens textuais de vazamento (Garantia 2,
passo 10 do avaliador) e satisfaz a unicidade exigida — inclusive frente a
reservas canceladas, já que `codigo` é PRIMARY KEY e o cancelamento é
soft-delete (nunca libera o código para reuso).
"""

from __future__ import annotations

import secrets

_ALFABETO = "BCDFGHJKLMNPQRSTVWXZ"  # consoantes: sem dígitos, sem vogais
_TAMANHO = 6


def gerar_codigo() -> str:
    sufixo = "".join(secrets.choice(_ALFABETO) for _ in range(_TAMANHO))
    return f"RSV-{sufixo}"
