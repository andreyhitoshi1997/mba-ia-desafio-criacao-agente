from __future__ import annotations

from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.apps.app import App
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.tools.function_tool import FunctionTool

from spikes.confirm_spike.fake_llm import FakeLlm
from spikes.confirm_spike.tool import acao_sensivel

APP_NAME = "aurora-spike"
VAR_DIR = Path(__file__).resolve().parents[2] / "var"
DB_URL = f"sqlite+aiosqlite:///{VAR_DIR / 'spike_sessions.db'}"

tool_sensivel = FunctionTool(acao_sensivel, require_confirmation=True)

root_agent = LlmAgent(
    name="root_spike",
    model=FakeLlm(),
    instruction="Chame acao_sensivel quando pedido.",
    tools=[tool_sensivel],
)

app = App(name=APP_NAME, root_agent=root_agent)


def novo_session_service() -> DatabaseSessionService:
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    return DatabaseSessionService(db_url=DB_URL)
