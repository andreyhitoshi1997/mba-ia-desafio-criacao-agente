"""Tool sensível do spike: grava 1 linha em spike.db quando aprovada."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

DB_PATH = Path(__file__).resolve().parents[2] / "var" / "spike.db"


def _conexao() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS spike_counter ("
        "chave TEXT PRIMARY KEY, criada_em TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    return conn


def acao_sensivel(valor: int, tool_context: ToolContext) -> dict:
    """Executa a ação protegida por confirmação, gravando de forma idempotente."""
    chave = str(tool_context.function_call_id)
    conn = _conexao()
    try:
        cur = conn.execute(
            "INSERT INTO spike_counter(chave) VALUES (?) ON CONFLICT(chave) DO NOTHING",
            (chave,),
        )
        gravou_agora = cur.rowcount == 1
    finally:
        conn.close()
    return {"status": "executada", "valor": valor, "gravou_agora": gravou_agora, "chave": chave}
