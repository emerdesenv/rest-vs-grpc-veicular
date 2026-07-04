#!/bin/bash
# ============================================================================
# Gera a PKI para mTLS: CA privada da frota + certificado do SERVIDOR + do CLIENTE
# Padrao do artigo: RSA-2048, SHA-256. CA valida 10 anos; certificados folha 365 dias.
#
# Uso:    bash gerar_pki.sh
# Saida:  pasta pki/ com ca.crt, server.key/crt, client.key/crt
#
# IMPORTANTE: IP_SERVIDOR abaixo precisa ser o IP do SERVIDOR (o Raspberry Pi).
# Se mudarem o IP, alterem aqui e gerem de novo, senao o TLS vai recusar a conexao.
# ============================================================================
set -e
IP_SERVIDOR="192.168.50.1"
DIR="pki"

mkdir -p "$DIR"
cd "$DIR"

echo ">> [1/3] Gerando a CA privada da frota (a raiz de confianca)..."
openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
  -keyout ca.key -out ca.crt -subj "/CN=Frota-CA-Privada"

echo ">> [2/3] Gerando o certificado do SERVIDOR (Raspberry Pi, IP $IP_SERVIDOR)..."
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout server.key -out server.csr -subj "/CN=gateway-server"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -sha256 -out server.crt \
  -extfile <(printf "subjectAltName=IP:%s" "$IP_SERVIDOR")

echo ">> [3/3] Gerando o certificado do CLIENTE (notebook)..."
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout client.key -out client.csr -subj "/CN=gateway-client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -sha256 -out client.crt

rm -f server.csr client.csr ca.srl
echo ""
echo ">> PKI gerada na pasta '$DIR/':"
echo "   ca.crt      -> a autoridade (copia vai nas DUAS maquinas)"
echo "   server.key  -> chave privada do servidor  (SO no Pi, NUNCA sai dele)"
echo "   server.crt  -> certificado do servidor"
echo "   client.key  -> chave privada do cliente   (SO no notebook)"
echo "   client.crt  -> certificado do cliente"
echo ""
echo ">> Conferencia (deve dizer 'OK' nas duas linhas):"
openssl verify -CAfile ca.crt server.crt
openssl verify -CAfile ca.crt client.crt
