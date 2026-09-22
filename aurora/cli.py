"""Comandos: `aurora restaurar` e `aurora serve`."""

from __future__ import annotations

import argparse
import logging

from dotenv import load_dotenv


def _restaurar() -> None:
    from aurora.infra.seed import restaurar

    restaurar()
    print("Dados restaurados a partir de dados/*.json (reservas, visitantes, sessões).")


def _serve() -> None:
    import uvicorn

    from aurora.infra.db import ativar_wal_no_arquivo_de_sessoes, migrar

    # ADR-7: só migração idempotente aqui, NUNCA seed — senão um restart
    # ressuscitaria reservas/visitantes já cancelados/alterados na conversa.
    migrar()
    ativar_wal_no_arquivo_de_sessoes()

    uvicorn.run("aurora.api.app:api", host="127.0.0.1", port=8000)


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(prog="aurora")
    subparsers = parser.add_subparsers(dest="comando", required=True)
    subparsers.add_parser("restaurar", help="Restaura reservas/visitantes/sessões ao estado inicial")
    subparsers.add_parser("serve", help="Sobe a API em http://localhost:8000")

    args = parser.parse_args()
    if args.comando == "restaurar":
        _restaurar()
    elif args.comando == "serve":
        _serve()


if __name__ == "__main__":
    main()
