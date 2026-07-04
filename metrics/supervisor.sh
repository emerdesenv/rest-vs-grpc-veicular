#!/bin/bash
# ============================================================================
# Supervisor de processo - ETAPA 5 (cenario C5 do artigo).
# Roda um comando (o servidor) num loop, reiniciando automaticamente se ele
# cair, e registrando cada inicio/queda com timestamp em supervisor_eventos.csv
# - isso e o "servico reiniciado automaticamente se entrar em falha" que o
# cenario C5 (ataque + rede degradada simultaneos) exige.
#
# Uso:
#   bash supervisor.sh "venv/bin/python3 servers/rest_server.py --seguranca mtls"
#   bash supervisor.sh "venv/bin/python3 servers/grpc_server.py --seguranca mtls"
#
# Parar com Ctrl+C (para o loop inteiro, nao so o processo filho da vez).
#
# NAO usa 'set -e' de proposito: o objetivo aqui e justamente sobreviver a
# falha do comando interno, nao abortar quando ele falhar.
# ============================================================================
COMANDO="$1"
LOG="supervisor_eventos.csv"

if [ -z "$COMANDO" ]; then
  echo 'Uso: bash supervisor.sh "comando do servidor entre aspas"'
  exit 1
fi

if [ ! -f "$LOG" ]; then
  echo "timestamp,evento" > "$LOG"
fi

echo ">> Supervisor ativo. Comando: $COMANDO"
echo ">> Eventos de inicio/queda vao para $LOG. Ctrl+C para parar o supervisor."

while true; do
  echo "$(date -Iseconds),iniciado" >> "$LOG"
  eval "$COMANDO"
  echo "$(date -Iseconds),caiu_reiniciando" >> "$LOG"
  echo ">> Processo caiu - reiniciando em 1s..."
  sleep 1
done
