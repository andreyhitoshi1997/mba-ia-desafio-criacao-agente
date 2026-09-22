"""Processo B: processo NOVO (interpretador novo). Abre a mesma sessão via
DatabaseSessionService, deriva a confirmação pendente pelos eventos, responde
aprovando, e confere que a tool executou exatamente uma vez.

Uso: uv run python -m spikes.confirm_spike.B <session_id>
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys

from google.adk.runners import Runner
from google.genai import types

from spikes.confirm_spike.agente import app, novo_session_service
from spikes.confirm_spike.confirmacoes import pendentes_da_sessao
from spikes.confirm_spike.tool import DB_PATH

USER_ID = "spike-user"


async def main(session_id: str) -> None:
    session_service = novo_session_service()
    runner = Runner(app=app, session_service=session_service)

    sessao = await session_service.get_session(
        app_name=app.name, user_id=USER_ID, session_id=session_id
    )
    if sessao is None:
        print("SESSAO_NAO_ENCONTRADA")
        return

    pendentes = pendentes_da_sessao(sessao.events)
    print(f"PENDENTES={list(pendentes.keys())}")
    if not pendentes:
        print("NENHUMA_PENDENCIA")
        return

    confirmacao_id = next(iter(pendentes))
    chamada = pendentes[confirmacao_id]
    print("DETALHES", json.dumps(chamada.args.get("originalFunctionCall"), default=str))

    resposta = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=confirmacao_id,
                    name="adk_request_confirmation",
                    response={"confirmed": True},
                )
            )
        ],
    )

    eventos_novos = []
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=resposta
    ):
        eventos_novos.append(event)
        print("EVENT", event.author, "role=", event.content.role if event.content else None)
        if event.content:
            for part in event.content.parts or []:
                if part.function_response:
                    print(
                        "  function_response",
                        part.function_response.id,
                        part.function_response.name,
                        json.dumps(part.function_response.response, default=str),
                    )
                if part.text:
                    print("  text", part.text)

    sessao_final = await session_service.get_session(
        app_name=app.name, user_id=USER_ID, session_id=session_id
    )
    print(f"TOTAL_EVENTOS_APOS_B={len(sessao_final.events)}")

    pendentes_apos = pendentes_da_sessao(sessao_final.events)
    print(f"PENDENTES_APOS_B={list(pendentes_apos.keys())}")

    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM spike_counter").fetchone()[0]
    conn.close()
    print(f"TOTAL_EFEITO_COLATERAL={total} (esperado 1)")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
