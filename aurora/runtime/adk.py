"""Singletons do runtime ADK: `App`, `Runner`, `DatabaseSessionService`.

Garantia 3: `DatabaseSessionService` sobre SQLite em arquivo separado
(`var/adk_sessions.db`) — sessões e eventos sobrevivem a um restart do
processo porque nunca vivem só em memória.
"""

from __future__ import annotations

from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService

from aurora.agents.root import assistente_aurora
from aurora.infra.caminhos import SESSOES_DB_URL

APP_NAME = "aurora"
USER_ID = "morador"  # fixo: a identidade real é o apartamento no state da sessão

app = App(name=APP_NAME, root_agent=assistente_aurora)

_session_service: DatabaseSessionService | None = None
_runner: Runner | None = None


def obter_session_service() -> DatabaseSessionService:
    global _session_service
    if _session_service is None:
        _session_service = DatabaseSessionService(
            db_url=SESSOES_DB_URL, connect_args={"timeout": 30.0}
        )
    return _session_service


def obter_runner() -> Runner:
    global _runner
    if _runner is None:
        _runner = Runner(app=app, session_service=obter_session_service())
    return _runner
