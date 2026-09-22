from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aurora.infra import caminhos


@pytest.fixture()
def banco_de_negocio_limpo(tmp_path, monkeypatch):
    """Isola cada teste num var/aurora.db temporário, já com schema e seed
    mínimo (apartamentos + areas), sem depender de ordem de execução."""
    db_path = tmp_path / "aurora.db"
    monkeypatch.setattr(caminhos, "NEGOCIO_DB_PATH", db_path)
    monkeypatch.setattr(caminhos, "VAR_DIR", tmp_path)

    from aurora.infra import db as db_module

    monkeypatch.setattr(db_module, "NEGOCIO_DB_PATH", db_path)
    monkeypatch.setattr(db_module, "VAR_DIR", tmp_path)
    monkeypatch.setattr(db_module._local, "conn", None, raising=False)

    db_module.migrar()
    conn = db_module.conexao()
    conn.execute("INSERT INTO apartamentos(numero, morador) VALUES ('101', 'Helena Prado')")
    conn.execute("INSERT INTO apartamentos(numero, morador) VALUES ('201', 'Luana Castro')")
    conn.execute(
        "INSERT INTO areas(id, nome, taxa) VALUES "
        "('salao-de-festas', 'Salão de festas', 150.0), "
        "('quadra', 'Quadra', 0.0)"
    )
    yield db_path
