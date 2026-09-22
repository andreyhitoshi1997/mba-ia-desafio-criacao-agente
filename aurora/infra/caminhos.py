"""Caminhos do projeto, resolvidos uma única vez."""

from __future__ import annotations

from pathlib import Path

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[2]
DADOS_DIR = RAIZ_DO_PROJETO / "dados"
VAR_DIR = RAIZ_DO_PROJETO / "var"

NEGOCIO_DB_PATH = VAR_DIR / "aurora.db"
SESSOES_DB_PATH = VAR_DIR / "adk_sessions.db"
SESSOES_DB_URL = f"sqlite+aiosqlite:///{SESSOES_DB_PATH}"
