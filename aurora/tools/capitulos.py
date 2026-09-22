"""Tool do especialista_regulamento (Garantia 4): parsing determinístico do
regulamento por capítulo, sem embeddings/RAG — não há exigência de busca
semântica, e devolver o arquivo inteiro é exatamente o que a garantia proíbe.

Devolve UM capítulo por vez. Roda numa sessão-filha de `AgentTool`: o texto
do capítulo nunca entra nos eventos da sessão principal, e o agente raiz não
importa este módulo nem tem o regulamento nas instruções.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from aurora.infra.caminhos import DADOS_DIR

_CAMINHO_REGULAMENTO = DADOS_DIR / "regulamento.md"
_PADRAO_CAPITULO = re.compile(r"^## Capítulo ([IVXLCDM]+): (.+)$", re.MULTILINE)

_INDICE_DE_ASSUNTOS = {
    "disposicoes gerais": "I",
    "geral": "I",
    "direitos": "II",
    "deveres": "II",
    "moradores": "II",
    "silencio": "III",
    "barulho": "III",
    "ruido": "III",
    "convivencia": "III",
    "festas": "III",
    "piscina": "IV",
    "academia": "V",
    "brinquedoteca": "V",
    "playground": "V",
    "salao de festas": "VI",
    "salao": "VI",
    "churrasqueira": "VI",
    "quadra": "VI",
    "reserva": "VI",
    "reservas": "VI",
    "portaria": "VII",
    "seguranca": "VII",
    "visitante": "VII",
    "visitantes": "VII",
    "acesso": "VII",
    "animais": "VIII",
    "animal": "VIII",
    "cachorro": "VIII",
    "pet": "VIII",
    "mudanca": "IX",
    "mudancas": "IX",
    "obra": "X",
    "obras": "X",
    "reforma": "X",
    "garagem": "XI",
    "veiculo": "XI",
    "veiculos": "XI",
    "estacionamento": "XI",
    "lixo": "XII",
    "reciclagem": "XII",
    "coleta": "XII",
    "infracao": "XIII",
    "infracoes": "XIII",
    "penalidade": "XIII",
    "penalidades": "XIII",
    "multa": "XIII",
    "disposicoes finais": "XIV",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


@lru_cache(maxsize=1)
def _capitulos() -> dict[str, dict[str, str]]:
    texto = _CAMINHO_REGULAMENTO.read_text(encoding="utf-8")
    matches = list(_PADRAO_CAPITULO.finditer(texto))
    capitulos: dict[str, dict[str, str]] = {}
    for indice, m in enumerate(matches):
        numero, titulo = m.group(1), m.group(2)
        inicio = m.end()
        fim = matches[indice + 1].start() if indice + 1 < len(matches) else len(texto)
        capitulos[numero] = {"titulo": titulo, "texto": texto[inicio:fim].strip()}
    return capitulos


def _resolver_capitulo(assunto: str) -> str | None:
    chave = _normalizar(assunto)
    if chave in _INDICE_DE_ASSUNTOS:
        return _INDICE_DE_ASSUNTOS[chave]
    for termo, numero in _INDICE_DE_ASSUNTOS.items():
        if termo in chave or chave in termo:
            return numero
    return None


def consultar_regulamento(assunto: str) -> dict:
    """Consulta o regulamento interno do condomínio por assunto, devolvendo
    só o capítulo relevante — nunca o documento inteiro.

    Args:
      assunto: palavra-chave do assunto (ex.: "piscina", "silencio", "animais",
        "garagem", "visitantes", "mudanca", "obras", "lixo", "penalidades").
    """
    numero = _resolver_capitulo(assunto)
    capitulos = _capitulos()
    if numero is None or numero not in capitulos:
        return {
            "encontrado": False,
            "assuntos_disponiveis": sorted(set(_INDICE_DE_ASSUNTOS.keys())),
        }
    capitulo = capitulos[numero]
    return {
        "encontrado": True,
        "capitulo": f"Capítulo {numero}: {capitulo['titulo']}",
        "texto": capitulo["texto"],
    }
