"""Restauração dos dados iniciais (comando `restaurar`).

ADR-7: só roda aqui, nunca no boot do `serve` — senão o restart do passo 13
do avaliador ressuscitaria reservas já canceladas. Os arquivos em `dados/`
são só leitura; este módulo nunca escreve neles.
"""

from __future__ import annotations

import json

from aurora.infra.caminhos import DADOS_DIR, NEGOCIO_DB_PATH, SESSOES_DB_PATH, VAR_DIR
from aurora.infra.db import conexao, migrar


def _ler_json(nome: str) -> list[dict]:
    caminho = DADOS_DIR / nome
    return json.loads(caminho.read_text(encoding="utf-8"))


def restaurar() -> None:
    VAR_DIR.mkdir(parents=True, exist_ok=True)

    for caminho in (NEGOCIO_DB_PATH, SESSOES_DB_PATH):
        caminho.unlink(missing_ok=True)
        for sufixo in ("-wal", "-shm"):
            caminho.with_name(caminho.name + sufixo).unlink(missing_ok=True)

    migrar()
    conn = conexao()

    for apto in _ler_json("apartamentos.json"):
        conn.execute(
            "INSERT INTO apartamentos(numero, morador) VALUES (?, ?)",
            (apto["numero"], apto["morador"]),
        )

    for area in _ler_json("areas.json"):
        conn.execute(
            "INSERT INTO areas(id, nome, taxa) VALUES (?, ?, ?)",
            (area["id"], area["nome"], area["taxa"]),
        )

    for reserva in _ler_json("reservas.json"):
        conn.execute(
            """
            INSERT INTO reservas(codigo, apartamento, area, data, status, idem_key)
            VALUES (?, ?, ?, ?, 'ativa', ?)
            """,
            (
                reserva["codigo"],
                reserva["apartamento"],
                reserva["area"],
                reserva["data"],
                f"seed:{reserva['codigo']}",
            ),
        )

    for visitante in _ler_json("visitantes.json"):
        conn.execute(
            "INSERT INTO visitantes(apartamento, nome, data, idem_key) VALUES (?, ?, ?, ?)",
            (
                visitante["apartamento"],
                visitante["nome"],
                visitante["data"],
                f"seed:{visitante['apartamento']}:{visitante['nome']}:{visitante['data']}",
            ),
        )
