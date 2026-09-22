"""Conexão SQLite do banco de negócio + migração idempotente.

Uma conexão por thread (`threading.local`) porque `sqlite3` recusa cruzar
threads por padrão (`check_same_thread=True`) e as tools rodam via
`asyncio.to_thread`, que usa um pool de threads — nunca a mesma thread duas
vezes seguidas. Compartilhar uma única conexão entre threads seria um bug de
concorrência silencioso.

WAL + `busy_timeout` aqui (Garantia 5): permite as rotas de verificação
lerem enquanto uma disputa de reserva escreve, sem `database is locked`.
"""

from __future__ import annotations

import sqlite3
import threading

from aurora.infra.caminhos import NEGOCIO_DB_PATH, SESSOES_DB_PATH, VAR_DIR

_local = threading.local()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS apartamentos (
    numero TEXT PRIMARY KEY,
    morador TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS areas (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    taxa REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    codigo TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL REFERENCES apartamentos(numero),
    area TEXT NOT NULL REFERENCES areas(id),
    data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativa',
    idem_key TEXT UNIQUE,
    criada_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_reserva_ativa
    ON reservas(area, data) WHERE status = 'ativa';

CREATE TABLE IF NOT EXISTS visitantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL REFERENCES apartamentos(numero),
    nome TEXT NOT NULL,
    data TEXT NOT NULL,
    idem_key TEXT UNIQUE,
    criada_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def conexao() -> sqlite3.Connection:
    """Conexão da thread atual, criada sob demanda. WAL + busy_timeout."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        VAR_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(NEGOCIO_DB_PATH, timeout=30.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def migrar() -> None:
    """CREATE TABLE/INDEX IF NOT EXISTS — seguro rodar a cada boot (ADR-7:
    nunca faz seed, só garante que o schema existe)."""
    conn = conexao()
    conn.executescript(_SCHEMA)


def ativar_wal_no_arquivo_de_sessoes() -> None:
    """`DatabaseSessionService` não ativa WAL para bancos em arquivo (só para
    `:memory:`). Sem isso, os `append_event` concorrentes do passo 14
    disputam o writer lock em modo `journal` padrão. Chamado uma vez no boot,
    antes do primeiro uso do `DatabaseSessionService` — WAL é uma propriedade
    do arquivo, não da conexão."""
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SESSOES_DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.close()
