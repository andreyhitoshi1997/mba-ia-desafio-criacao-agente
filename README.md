# Assistente do Residencial Aurora

API em Python + Google ADK que expõe o assistente virtual dos moradores do
Residencial Aurora: reserva de áreas comuns, cancelamento de reservas,
autorização de visitantes e consulta ao regulamento interno — com as regras
críticas do condomínio garantidas em código, não em prompt.

Desafio do MBA "Regra é regra". Fork do repositório base
[devfullcycle/mba-ia-desafio-criacao-agente](https://github.com/devfullcycle/mba-ia-desafio-criacao-agente).

## Arquitetura

Um agente principal (`assistente_aurora`) e dois especialistas, todos
`LlmAgent` do Google ADK, definidos em `aurora/agents/`.

### `assistente_aurora` (`aurora/agents/root.py`) — agente raiz

É quem conversa com o morador e a **única autoridade transacional**: detém
todas as tools que mutam estado — `reservar_area`, `cancelar_reserva`,
`autorizar_visitante` (`aurora/tools/reservas.py`, `aurora/tools/visitantes.py`)
— e é o único autor de pedidos de confirmação da sessão.

Essa escolha não é estética: um spike dedicado (`spikes/confirm_spike/`,
resultado documentado em `spikes/confirm_spike/RESULTADO.md`) mostrou que o
`Runner` do ADK só encontra de volta o agente certo para retomar uma
confirmação pendente quando esse agente é o autor original da chamada — com
sub-agentes e transferência, ou tools de confirmação dentro de um
especialista, a retomada pode falhar **em silêncio**: a rota de confirmação
responde 200 e a ação nunca executa. Com uma única autoridade transacional,
esse modo de falha deixa de existir por construção.

### `especialista_agenda` (`aurora/agents/agenda.py`) — acionado via `AgentTool`

Único agente que consulta a agenda de área comum (`consultar_disponibilidade`,
`listar_areas_comuns`, em `aurora/tools/agenda.py`). Devolve só
`{"disponivel": bool}` — nunca o apartamento dono de uma reserva alheia.

### `especialista_regulamento` (`aurora/agents/regulamento.py`) — acionado via `AgentTool`

Único agente que lê texto do regulamento interno (`consultar_regulamento`,
em `aurora/tools/capitulos.py`), devolvendo **um capítulo por vez**, nunca o
documento inteiro.

### Por que `AgentTool` e não sub-agentes com transferência

`AgentTool` (`google.adk.tools.agent_tool.AgentTool`) roda o especialista
numa **sessão-filha efêmera** — os eventos dessa sessão nunca se misturam
aos da sessão principal, só a resposta final do especialista retorna como
resultado da tool. Isso dá, de graça, duas propriedades que o desafio exige:

- o texto de um capítulo do regulamento nunca aparece nos eventos da sessão
  principal (Garantia 4);
- mesmo que um especialista "soubesse" algo sobre outro apartamento, isso
  nunca vazaria para a conversa do morador (reforça a Garantia 2 — embora,
  como abaixo, a proteção primária dessa garantia seja outra).

Cada especialista existe para **estreitar o que chega ao agente principal**,
não para dividir carga de trabalho arbitrariamente.

### Tools acessam dados reais, nunca "memória" do modelo

Todas as tools de reserva/visitante chamam a camada `aurora/aplicacao/`, que
chama `aurora/infra/repositorio.py` (SQLite) — o modelo nunca inventa nem
lembra um código de reserva, uma data ocupada ou um nome de visitante; tudo
vem de uma consulta real ao banco a cada chamada.

## Garantias

Para cada garantia: o arquivo, o trecho relevante, e por que a proteção não
depende de o modelo "decidir certo".

### Garantia 1 — cobrança ou acesso só com confirmação

**`aurora/tools/reservas.py`** — `reservar_area` só pede confirmação quando a
área tem taxa (a decisão vem do banco, não do modelo):

```python
async def _area_requer_confirmacao(area: str, **_ignorado) -> bool:
    return await asyncio.to_thread(area_gera_cobranca, _repositorio, area)

reservar_area_tool = FunctionTool(
    reservar_area, require_confirmation=_area_requer_confirmacao
)
```

**`aurora/tools/visitantes.py`** — `autorizar_visitante` sempre exige
confirmação (libera acesso), e a instrução do agente raiz explicita que
nenhum texto do morador ("já confirmei", "pode liberar direto") substitui a
rota real:

```python
autorizar_visitante_tool = FunctionTool(autorizar_visitante, require_confirmation=True)
```

**`aurora/runtime/confirmacoes.py`** — `confirmacoes_pendentes` é estado
**derivado dos eventos da sessão**, nunca uma tabela paralela:

```python
def pendentes_da_sessao(eventos) -> dict[str, "types.FunctionCall"]:
    pedidos: dict = {}
    respondidos: set[str] = set()
    for evento in eventos:
        for chamada in evento.get_function_calls():
            if chamada.name == NOME_CONFIRMACAO and chamada.id:
                pedidos[chamada.id] = chamada
        for resposta in evento.get_function_responses():
            if resposta.name == NOME_CONFIRMACAO and resposta.id:
                respondidos.add(resposta.id)
    return {id_: fc for id_, fc in pedidos.items() if id_ not in respondidos}
```

**`aurora/api/app.py`**, rota `POST /sessoes/{session_id}/confirmacoes` — o
409 é decidido **antes** de qualquer chamada ao Runner:

```python
pendentes = pendentes_da_sessao(sessao.events)
if corpo.id not in pendentes:
    raise HTTPException(status_code=409, detail="confirmação não está pendente nesta sessão")
```

**Por que não depende do modelo:** validamos empiricamente (spike, célula 1)
que, sem esse gate, o próprio ADK **reexecuta** a tool ao receber de novo a
resposta de uma confirmação já respondida — reenviar `{"id": C1, ...}` faz o
Runner casar `C1` com a `function_call` original e rodar a tool de novo. O
409 do contrato só existe porque a API confere a pendência lendo os eventos
gravados, e nunca invoca o Runner quando o id não está pendente — "negar" ou
"eu já confirmei por aqui" na conversa não passam perto de uma tool que gera
cobrança ou libera acesso; só a rota dedicada aciona o `Runner` com uma
resposta de confirmação real.

Defesa adicional contra reexecução mesmo que o gate falhe: a chave de
idempotência do INSERT é o `function_call_id` da chamada original (estável
entre a primeira chamada e qualquer retomada — validado no spike), não um
valor gerado a cada execução:

```python
idem_key=str(tool_context.function_call_id),
```

Ver `aurora/infra/repositorio.py`, `inserir_reserva`/`inserir_visitante`
(`ON CONFLICT(idem_key) DO NOTHING`).

### Garantia 2 — cada sessão pertence a um apartamento

**`aurora/api/app.py`**, rota `POST /sessoes` — o apartamento é gravado uma
única vez, no **state da sessão gerenciado pelo ADK**, no momento da criação:

```python
sessao = await obter_session_service().create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    state={"apartamento": corpo.apartamento},
)
```

**`aurora/tools/reservas.py`** / **`aurora/tools/visitantes.py`** — todas as
tools lêem o apartamento do `state`, nunca de um argumento:

```python
async def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    apartamento = tool_context.state["apartamento"]
    ...
```

**Por que não depende do modelo — é estrutural, não instruído:** a
assinatura das tools não declara `apartamento` como parâmetro. O ADK omite o
parâmetro de contexto (`tool_context`) do schema enviado ao Gemini — o
modelo **não recebe esse campo para preencher**, com ou sem prompt
injection, porque function calling é transporte estruturado, não texto
livre. Isso é verificado em `tests/test_declaracoes_de_tools.py`:

```python
def test_reservar_area_so_expoe_area_e_data():
    assert _propriedades(reservar_area_tool) == {"area", "data"}
```

Defesa em profundidade contra regressão futura (alguém adicionar um
parâmetro `apartamento` por descuido em uma tool nova):
**`aurora/agents/guardrails.py`**, registrado como `before_tool_callback` do
agente raiz em `aurora/agents/root.py`:

```python
_PARAMETROS_PROIBIDOS = {"apartamento", "apto", "unidade", "morador"}

def bloquear_apartamento_escolhido_pelo_modelo(tool, args, tool_context):
    invasores = _PARAMETROS_PROIBIDOS & args.keys()
    if invasores:
        return {"error": f"parametro nao permitido: {sorted(invasores)}"}
    return None
```

**Disponibilidade sem vazar dono da reserva:** `aurora/tools/agenda.py`,
`consultar_disponibilidade`, devolve só um booleano:

```python
async def consultar_disponibilidade(area: str, data: str) -> dict:
    livre = await asyncio.to_thread(data_esta_livre, _repositorio, area, data)
    return {"disponivel": livre}
```

**Cancelamento nunca alcança reserva alheia:** `aurora/tools/reservas.py`,
`cancelar_reserva`, recebe `(area, data)` — nunca um `codigo` — e o
`WHERE apartamento = ?` do repositório (`aurora/infra/repositorio.py`,
`cancelar_reserva`) é sempre escopado pelo apartamento da sessão. Se a
reserva pertence a outro apartamento, a busca simplesmente não encontra
nada: `{"status": "nenhuma_reserva_sua"}`.

### Garantia 3 — nada se perde no reinício

**`aurora/runtime/adk.py`** — `DatabaseSessionService` sobre SQLite em
arquivo, separado do banco de negócio:

```python
_session_service = DatabaseSessionService(
    db_url=SESSOES_DB_URL, connect_args={"timeout": 30.0}
)
```

**`aurora/cli.py`**, comando `serve` — no boot só roda migração idempotente
(nunca semeia dados):

```python
migrar()
ativar_wal_no_arquivo_de_sessoes()
uvicorn.run("aurora.api.app:api", host="127.0.0.1", port=8000)
```

**Por que não depende do modelo:** sessão e eventos são persistidos pelo
próprio ADK a cada turno, em arquivo (`var/adk_sessions.db`); reservas e
visitantes são persistidos pelo repositório SQLite (`var/aurora.db`) a cada
gravação — nenhum dos dois vive em memória do processo. O `restaurar`
(`aurora/infra/seed.py`) é o único comando que apaga esses arquivos; `serve`
nunca apaga nada, só garante que as tabelas existem
(`CREATE TABLE IF NOT EXISTS`). Validado manualmente reiniciando a API no
meio de uma conversa (passo 13 do fluxo do avaliador — ver "Como rodar").

### Garantia 4 — o regulamento é consultado, não carregado

**`aurora/tools/capitulos.py`** — parsing determinístico por capítulo, sem
embeddings (não há exigência de busca semântica e seria custo sem
benefício); devolve **um capítulo só**:

```python
def consultar_regulamento(assunto: str) -> dict:
    numero = _resolver_capitulo(assunto)
    ...
    return {"encontrado": True, "capitulo": ..., "texto": capitulo["texto"]}
```

**`aurora/agents/root.py`** — a instrução do agente raiz não contém uma
linha do regulamento; o módulo `tools/capitulos.py` nem é importado por
`root.py` (só por `agents/regulamento.py`, do especialista):

```python
_INSTRUCAO = """\
Você é o assistente virtual do Residencial Aurora, ...
"""  # nenhuma menção a artigo/capítulo do regulamento
```

**Por que não depende do modelo:** o texto do capítulo só existe dentro da
sessão-filha que o `AgentTool(especialista_regulamento)` cria e descarta a
cada chamada — estruturalmente, não há como um capítulo não pedido
atravessar para a sessão principal, porque a sessão-filha nunca é persistida
como parte da sessão do morador. Testado em `tests/test_regulamento.py`
(`test_devolve_um_capitulo_so_nunca_o_documento_inteiro`).

### Garantia 5 — dois moradores, uma reserva

**`aurora/infra/db.py`** — a exclusividade é um índice único parcial no
banco, avaliado pelo SQLite no instante do `INSERT`, não por uma checagem
em Python antes de gravar:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_reserva_ativa
    ON reservas(area, data) WHERE status = 'ativa';
```

**`aurora/infra/repositorio.py`**, `inserir_reserva` — o `INSERT` é a
própria checagem; um `IntegrityError` do índice único vira uma resposta de
domínio, nunca uma exceção que escaparia como HTTP 500:

```python
try:
    cursor = conn.execute(
        "INSERT INTO reservas(codigo, apartamento, area, data, idem_key) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(idem_key) DO NOTHING",
        (codigo, comando.apartamento, comando.area, comando.data, comando.idem_key),
    )
except sqlite3.IntegrityError:
    if self.existe_reserva_ativa(comando.area, comando.data):
        return ResultadoDaReserva.agenda_ocupada()
    ...
```

**Por que não depende do modelo, nem só de uma checagem prévia:** entre
"consultar se está livre" e "gravar" sempre existe uma janela onde outra
reserva pode entrar (TOCTOU) — por isso a exclusividade real está no
`UNIQUE INDEX ... WHERE status = 'ativa'`, avaliado pelo próprio SQLite de
forma atômica no `INSERT`. `aurora/infra/db.py` ativa `PRAGMA
journal_mode=WAL` e `PRAGMA busy_timeout=30000` para que a segunda escrita
espere e resolva por constraint, em vez de falhar com `database is locked`.
Validado sob concorrência real (não sequencial) em
`tests/test_concorrencia_reservas.py` (duas `threading.Thread` reais
disputando a mesma área/data) e em `scripts/teste_concorrencia.sh` /
`scripts/teste_concorrencia_stress.py` (via HTTP, réplica do passo 14).

## Como rodar

### Pré-requisitos

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Uma chave de API do [Google AI Studio](https://aistudio.google.com/apikey)

### Variáveis de ambiente (`.env`)

```bash
cp .env.example .env
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GOOGLE_API_KEY` | sim | Chave do Google AI Studio (também aceita `GEMINI_API_KEY`). |
| `AURORA_MODEL` | não | Modelo Gemini padrão para os três agentes (recomendado: `gemini-flash-lite-latest` — alias sempre atualizado, com cota de tier gratuito mais folgada nos nossos testes do que apontar um modelo fixo como `gemini-2.5-flash`; relevante porque o fluxo do avaliador faz várias dezenas de chamadas ao modelo numa janela curta). |
| `AURORA_MODEL_ROOT` / `AURORA_MODEL_AGENDA` / `AURORA_MODEL_REGULAMENTO` | não | Sobrescreve o modelo de um agente específico. |

### Instalar

```bash
uv sync
```

> O projeto é gerenciado como app (`[tool.uv] package = false`), não como
> biblioteca instalável: rode os comandos abaixo com `uv run` a partir da
> raiz do repositório. Isso evita depender do mecanismo de instalação
> editável do `pip`/`uv` para o próprio pacote `aurora` — numa combinação
> específica de build do Python 3.12 usada pelo `uv` neste ambiente, o
> `.pth` editável é gerado com a flag de arquivo oculto do macOS, e o
> `site.py` do CPython passa a ignorá-lo silenciosamente, quebrando `import
> aurora`. Com `package = false`, `uv sync` só resolve as dependências, e
> `uv run python -m aurora.cli ...` funciona porque o Python sempre insere o
> diretório atual no `sys.path` ao rodar um módulo com `-m`.

### Restaurar os dados iniciais

```bash
uv run python -m aurora.cli restaurar
```

Recria `var/aurora.db` a partir de `dados/*.json` (apartamentos, áreas,
reservas, visitantes) e apaga `var/adk_sessions.db` — ambiente limpo e
determinístico. Os arquivos em `dados/` nunca são alterados.

### Subir a API

```bash
uv run python -m aurora.cli serve
```

Sobe em `http://localhost:8000`. Reiniciar (`Ctrl+C` e rodar de novo o
mesmo comando, **sem** `restaurar`) preserva sessões e dados (Garantia 3).

### Verificar

```bash
curl -s localhost:8000/apartamentos/101/reservas
curl -s localhost:8000/apartamentos/302/visitantes
```

Com a API rodando, o roteiro completo do avaliador pode ser reproduzido com:

```bash
uv run pytest tests/ -q                        # garantias testáveis sem LLM
./scripts/verificar_fluxo_avaliador.sh          # passos 2–12 e 14, via HTTP
./scripts/teste_concorrencia.sh 2030-05-11      # só o passo 14 (disputa real)
uv run python scripts/teste_concorrencia_stress.py  # 20 rodadas de disputa
```

Os passos 1 (clone limpo), 13 (reiniciar a API no meio da conversa) e 15
(auditoria do repositório) são, por natureza, manuais — não dá para
automatizar um restart de processo de dentro do próprio processo.

### Nota sobre limites de tier gratuito

Chaves novas do Google AI Studio podem ter cota diária bem mais restrita do
que "algumas dezenas de chamadas por conversa" (nos nossos testes, 20
requisições/dia para um modelo específico numa chave nova). Isso é externo
ao código, mas afeta a execução do fluxo completo: os três agentes têm
`retry_config` com backoff (`aurora/agents/resiliencia.py`) para picos
transitórios de RPM, porém uma cota diária esgotada não tem como ser
contornada por retry — só reseta em 24h ou some com billing habilitado no
projeto do Google AI Studio (https://ai.studio/projects). Se o fluxo do
avaliador falhar com `429`/`402` em vez de um erro do assistente, é esse o
sintoma, não um bug de código.
