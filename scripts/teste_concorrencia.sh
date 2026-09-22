#!/usr/bin/env bash
# Reproduz o passo 14 do avaliador: dois apartamentos disputam a mesma
# área/data e aprovam ao mesmo tempo. As duas respostas devem ser 200, e a
# soma das reservas nos dois apartamentos deve ser exatamente 1.
set -euo pipefail
BASE="${AURORA_BASE_URL:-http://localhost:8000}"
DATA="${1:-2030-05-11}"

S3=$(curl -s -X POST "$BASE/sessoes" -H 'Content-Type: application/json' -d '{"apartamento":"101"}' | jq -r .session_id)
S4=$(curl -s -X POST "$BASE/sessoes" -H 'Content-Type: application/json' -d '{"apartamento":"201"}' | jq -r .session_id)

R3=$(curl -s -X POST "$BASE/sessoes/$S3/mensagens" -H 'Content-Type: application/json' \
  -d "{\"texto\":\"Reserve o salão de festas para $DATA.\"}")
R4=$(curl -s -X POST "$BASE/sessoes/$S4/mensagens" -H 'Content-Type: application/json' \
  -d "{\"texto\":\"Reserve o salão de festas para $DATA.\"}")

ID3=$(echo "$R3" | jq -r '.confirmacoes_pendentes[0].id')
ID4=$(echo "$R4" | jq -r '.confirmacoes_pendentes[0].id')

if [ "$ID3" = "null" ] || [ "$ID4" = "null" ]; then
  echo "FALHA: uma das duas sessões não gerou confirmação pendente" >&2
  echo "R3=$R3" >&2
  echo "R4=$R4" >&2
  exit 1
fi

curl -s -o /tmp/out3.json -w 'HTTP_S3=%{http_code}\n' -X POST "$BASE/sessoes/$S3/confirmacoes" \
  -H 'Content-Type: application/json' -d "{\"id\":\"$ID3\",\"confirmado\":true}" &
curl -s -o /tmp/out4.json -w 'HTTP_S4=%{http_code}\n' -X POST "$BASE/sessoes/$S4/confirmacoes" \
  -H 'Content-Type: application/json' -d "{\"id\":\"$ID4\",\"confirmado\":true}" &
wait

N101=$(curl -s "$BASE/apartamentos/101/reservas" | jq "[.[] | select(.area==\"salao-de-festas\" and .data==\"$DATA\")] | length")
N201=$(curl -s "$BASE/apartamentos/201/reservas" | jq "[.[] | select(.area==\"salao-de-festas\" and .data==\"$DATA\")] | length")
TOTAL=$((N101 + N201))

echo "TOTAL=$TOTAL (esperado 1)"
if [ "$TOTAL" -ne 1 ]; then
  echo "FALHA: esperava exatamente 1 reserva ativa, achou $TOTAL" >&2
  exit 1
fi
echo "OK: exclusividade da reserva sob disputa real confirmada."
