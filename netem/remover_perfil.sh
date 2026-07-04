#!/bin/bash
# ============================================================================
# Remove qualquer perfil de rede (tc netem) aplicado por aplicar_perfil.sh,
# devolvendo a interface ao comportamento normal (cabo limpo, sem
# degradacao). Rode isso entre um perfil e outro, ou ao terminar os testes
# de rede do dia.
#
# Uso: sudo bash remover_perfil.sh
#
# IFACE precisa ser a mesma interface usada em aplicar_perfil.sh.
# ============================================================================
set -e
IFACE="eth0"

echo ">> Removendo regras de rede (netem) de $IFACE..."
sudo tc qdisc del dev "$IFACE" root 2>/dev/null || echo "   (nao havia nenhuma regra ativa)"

echo ""
echo ">> Conferencia (nao deve aparecer 'netem' na saida abaixo):"
tc qdisc show dev "$IFACE"
