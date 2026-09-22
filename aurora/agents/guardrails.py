"""Defesa em profundidade do agente raiz.

A defesa PRIMÁRIA da Garantia 2 é a assinatura das tools: nenhuma delas
declara um parâmetro `apartamento` no schema exposto ao modelo (verificado:
`FunctionTool` ignora o parâmetro `tool_context` na declaração enviada ao
Gemini) — o modelo não tem como preencher o que nunca lhe é oferecido, nem
com prompt injection, porque function calling é transporte estruturado, não
texto livre.

`bloquear_apartamento_escolhido_pelo_modelo` é a rede de segurança contra
REGRESSÃO: se algum dia uma tool nova ganhar um parâmetro `apartamento` por
descuido, este callback recusa a chamada em vez de deixar passar em silêncio.
É também o trecho que a seção Garantias do README aponta para "nenhuma tool
que aceite um apartamento escolhido pelo modelo sem validar contra o da
sessão" (passo 15 do avaliador).

`registrar_erro_de_tool` é a rede de segurança da Garantia 5: nenhuma
exceção de tool deve virar HTTP 500 (o ADK não intercepta exceção nenhuma —
verificado no código-fonte 2.9.2). O repositório já não deixa
`sqlite3.IntegrityError` escapar; este callback só existe para o caso de bug
não previsto, convertendo em erro de domínio em vez de propagar.
"""

from __future__ import annotations

import logging

_PARAMETROS_PROIBIDOS = {"apartamento", "apto", "unidade", "morador"}

logger = logging.getLogger("aurora.guardrails")


def bloquear_apartamento_escolhido_pelo_modelo(tool, args, tool_context):
    invasores = _PARAMETROS_PROIBIDOS & args.keys()
    if invasores:
        logger.error("tool=%s tentou receber parametro proibido=%s", tool.name, invasores)
        return {"error": f"parametro nao permitido: {sorted(invasores)}"}
    return None


def registrar_erro_de_tool(tool, args, tool_context, error):
    logger.error("erro_nao_tratado_na_tool tool=%s args=%s erro=%s", tool.name, args, error)
    return {"error": "Não foi possível concluir a ação agora. Tente novamente."}
