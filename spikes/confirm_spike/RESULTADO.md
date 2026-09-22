# Resultado do spike de confirmação (ADR-8)

**Ambiente:** `google-adk==2.9.2`, Python 3.12, `DatabaseSessionService` sobre
SQLite em arquivo (`sqlite+aiosqlite:///var/spike_sessions.db`), sem
`ResumabilityConfig`. LLM determinístico (`fake_llm.py`), sem depender de
`GEMINI_API_KEY` — isola o mecanismo de retomada do Runner/SessionService de
qualquer variabilidade de um LLM real.

## Célula vencedora: **1** (tool de confirmação declarada direto no root agent)

Protocolo executado literalmente como "processo A" / "processo B" (dois
`uv run python -m ...` separados, ou seja, dois processos distintos, cada um
com seu próprio Runner/App recém-criado — equivalente a um restart real):

```
$ uv run python -m spikes.confirm_spike.A
SESSION_ID=8d64df10-b877-4de0-90b3-ac4b69c2e2b9
...
EVENT root_spike role= user
  function_response fc-call-1 acao_sensivel {"error": "This tool call requires confirmation..."}
  requested_tool_confirmations ['fc-call-1']
TOTAL_EVENTOS_APOS_A=4

$ uv run python -m spikes.confirm_spike.B 8d64df10-b877-4de0-90b3-ac4b69c2e2b9
PENDENTES=['adk-1eaab95d-d1de-4582-8383-a2bda826e200']
DETALHES {"id": "fc-call-1", "args": {"valor": 42}, "name": "acao_sensivel"}
EVENT root_spike role= user
  function_response fc-call-1 acao_sensivel {"status": "executada", "valor": 42, "gravou_agora": true, ...}
EVENT root_spike role= model
  text ação concluída
TOTAL_EVENTOS_APOS_B=7
PENDENTES_APOS_B=[]
TOTAL_EFEITO_COLATERAL=1 (esperado 1)
```

**Critério de saída atingido:** processo B, num interpretador novo, carregou a
sessão persistida, derivou a pendência pelos eventos, respondeu e a tool
executou **exatamente uma vez**.

## Achados que viram decisão de código (não teoria — medidos)

1. **O `function_response` de retomada é endereçado ao id do `adk_request_confirmation`
   (`C1`), não ao id da tool original (`F1`).** Formato exato:
   ```python
   types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
       id=C1, name="adk_request_confirmation", response={"confirmed": bool}))])
   ```
2. **O evento com o `function_response` de erro para `F1`** ("this tool call requires
   confirmation...") já é gravado na PRIMEIRA invocação, com `author=<nome do
   agente>` e `content.role="user"`. Isso importa porque o parser de retomada do
   ADK (`request_confirmation.py`) filtra por `event.author == "user"` (campo
   `author`, não `role`) para achar a resposta do cliente — um evento de tool
   nunca é confundido com uma resposta de confirmação, mesmo tendo `role="user"`.
3. **Reenvio da mesma confirmação sem gate prévio FAZ o ADK re-executar a tool**
   (confirmado isolando o teste, chamando `runner.run_async` de novo com o
   mesmo `id=C1`): a tool rodou de novo (`gravou_agora: False` na segunda vez,
   ou seja, ela tentou gravar de novo). Duas consequências:
   - **O 409 do contrato (`POST /confirmacoes` com id já respondido) tem que
     ser decidido ANTES de tocar o Runner**, varrendo os eventos da sessão —
     nunca delegado ao ADK. É o que `runtime/confirmacoes.py` faz.
   - **A chave de idempotência de negócio precisa sobreviver a essa
     re-execução mesmo quando o gate falhar por algum motivo.** Usar
     `function_call_id` (`F1`, estável entre a primeira chamada e qualquer
     retomada) como `idem_key` do INSERT é o que, neste teste, manteve
     `TOTAL_EFEITO_COLATERAL_SEM_GATE=1` mesmo com o Runner reexecutando a
     tool. Um `uuid4()` gerado dentro da tool teria duplicado.
4. **`tool_context.tool_confirmation.payload` não é necessário**: o dado que
   a rota precisa devolver em `detalhes` (`originalFunctionCall.args`) já está
   nos `args` do próprio `function_call` `adk_request_confirmation`, legível
   direto dos eventos — sem exigir round-trip de payload custom.

## Decisão final de arquitetura (encerra ADR-8)

Topologia adotada: **todas as tools que mutam estado (`reservar_area`,
`cancelar_reserva`, `autorizar_visitante`) ficam no agente raiz**, sem
`sub_agents`/transferência e sem `AgentTool`. Nenhum `ResumabilityConfig` é
necessário. Plano B/C do ADR-8 não são acionados — a topologia nativa funciona
na primeira célula testada.

Chave de idempotência de negócio: `tool_context.function_call_id` (não
`uuid4`), gravada como `idem_key UNIQUE` na tabela de negócio.

O gate de 409 (`POST /confirmacoes`) é sempre pré-Runner: a rota deriva as
pendências da sessão, e só invoca `runner.run_async` se o `id` recebido
estiver no conjunto pendente — replicado em `src/aurora/runtime/confirmacoes.py`.
