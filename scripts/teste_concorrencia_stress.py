"""Estresse estatístico da Garantia 5 via HTTP real (não só o repositório):
20 rodadas de disputa simultânea entre dois apartamentos, cada uma numa
data nova, usando asyncio.gather para paralelismo real de verdade.

Uso: uv run python scripts/teste_concorrencia_stress.py
(API já rodando em http://localhost:8000)
"""

from __future__ import annotations

import asyncio

import httpx

BASE = "http://localhost:8000"


async def disputar(cliente: httpx.AsyncClient, apartamento: str, data: str) -> dict:
    sessao = (await cliente.post(f"{BASE}/sessoes", json={"apartamento": apartamento})).json()
    sid = sessao["session_id"]
    resposta = (
        await cliente.post(
            f"{BASE}/sessoes/{sid}/mensagens",
            json={"texto": f"Reserve o salão de festas para {data}."},
        )
    ).json()
    pendentes = resposta.get("confirmacoes_pendentes") or []
    if not pendentes:
        return {"apartamento": apartamento, "status": "sem_confirmacao"}
    conf_id = pendentes[0]["id"]
    resp = await cliente.post(
        f"{BASE}/sessoes/{sid}/confirmacoes",
        json={"id": conf_id, "confirmado": True},
    )
    return {"apartamento": apartamento, "status": resp.status_code}


async def rodada(data: str) -> None:
    async with httpx.AsyncClient(timeout=60) as cliente:
        resultados = await asyncio.gather(
            disputar(cliente, "101", data),
            disputar(cliente, "201", data),
        )
        assert all(r["status"] == 200 for r in resultados), resultados
        totais = await asyncio.gather(
            cliente.get(f"{BASE}/apartamentos/101/reservas"),
            cliente.get(f"{BASE}/apartamentos/201/reservas"),
        )
        total = sum(
            len([x for x in r.json() if x["area"] == "salao-de-festas" and x["data"] == data])
            for r in totais
        )
        assert total == 1, f"data={data} total={total} (esperado 1)"
        print(f"ok data={data} total={total}")


async def main() -> None:
    for i in range(20):
        data = f"2031-02-{i + 1:02d}"
        await rodada(data)
    print("20/20 rodadas OK — exclusividade sob disputa nunca falhou.")


if __name__ == "__main__":
    asyncio.run(main())
