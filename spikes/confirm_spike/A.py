"""Processo A: cria sessão, dispara a tool que pede confirmação, imprime
os eventos crus (para inspecionar o formato real) e sai sem responder.
"""

from __future__ import annotations

import asyncio
import json

from google.adk.runners import Runner
from google.genai import types

from spikes.confirm_spike.agente import app, novo_session_service

USER_ID = "spike-user"


async def main() -> None:
    session_service = novo_session_service()
    runner = Runner(app=app, session_service=session_service)

    session = await session_service.create_session(
        app_name=app.name, user_id=USER_ID
    )
    print(f"SESSION_ID={session.id}")

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part(text="execute a acao sensivel")]
        ),
    ):
        print("EVENT", event.author, "role=", event.content.role if event.content else None)
        if event.content:
            for part in event.content.parts or []:
                if part.function_call:
                    print(
                        "  function_call",
                        part.function_call.id,
                        part.function_call.name,
                        json.dumps(part.function_call.args, default=str),
                    )
                if part.function_response:
                    print(
                        "  function_response",
                        part.function_response.id,
                        part.function_response.name,
                        json.dumps(part.function_response.response, default=str),
                    )
                if part.text:
                    print("  text", part.text)
        if event.actions and event.actions.requested_tool_confirmations:
            print("  requested_tool_confirmations", list(event.actions.requested_tool_confirmations.keys()))

    sessao_final = await session_service.get_session(
        app_name=app.name, user_id=USER_ID, session_id=session.id
    )
    print(f"TOTAL_EVENTOS_APOS_A={len(sessao_final.events)}")


if __name__ == "__main__":
    asyncio.run(main())
