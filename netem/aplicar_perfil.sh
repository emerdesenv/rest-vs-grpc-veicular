#!/bin/bash
# ============================================================================
# Aplica um perfil de rede movel (3G/4G/LTE) na interface do Pi, usando
# tc netem - simula a degradacao de conexao movel descrita no artigo
# (Secao 5.4), calibrada com base em medicoes Opensignal (2023) para o Brasil.
#
# Uso:    sudo bash aplicar_perfil.sh {3g|4g|lte}
# Reverter: sudo bash remover_perfil.sh (no mesmo diretorio)
#
# IMPORTANTE: IFACE abaixo precisa ser a interface do CABO (a mesma dos IPs
# 192.168.50.x), NUNCA a interface Wi-Fi/internet do Pi - aplicar netem na
# interface errada pode deixar o Pi lento/instavel para outras conexoes.
# Confira com "ip addr" antes de rodar se tiver duvida.
#
# Aplica so no sentido de saida do Pi (nao usa ifb/redirecionamento): isso
# ja e suficiente para refletir o atraso completo na medicao de ida-e-volta
# que os clientes fazem (RTT = ida quase sem atraso + volta com o atraso
# configurado = RTT total ~= valor do perfil). Simplificacao deliberada.
# ============================================================================
set -e
IFACE="eth0"
PERFIL="$1"

if [ -z "$PERFIL" ]; then
  echo "Uso: sudo bash aplicar_perfil.sh {3g|4g|lte}"
  exit 1
fi

case "$PERFIL" in
  3g)
    DELAY="100ms 20ms"; LOSS="2%"; RATE="2mbit"
    ;;
  4g)
    DELAY="35ms 10ms"; LOSS="0.5%"; RATE="20mbit"
    ;;
  lte)
    DELAY="15ms 5ms"; LOSS="0.1%"; RATE="50mbit"
    ;;
  *)
    echo "Perfil invalido: '$PERFIL'. Use 3g, 4g ou lte."
    exit 1
    ;;
esac

echo ">> Removendo qualquer regra netem anterior em $IFACE (se houver)..."
sudo tc qdisc del dev "$IFACE" root 2>/dev/null || true

echo ">> Aplicando perfil '$PERFIL' em $IFACE: delay $DELAY, loss $LOSS, rate $RATE..."
sudo tc qdisc add dev "$IFACE" root netem delay $DELAY loss $LOSS rate $RATE

echo ""
echo ">> Conferencia (deve mostrar o netem com os parametros acima):"
tc qdisc show dev "$IFACE"
echo ""
echo ">> Perfil '$PERFIL' ativo em $IFACE. Para reverter: sudo bash remover_perfil.sh"
