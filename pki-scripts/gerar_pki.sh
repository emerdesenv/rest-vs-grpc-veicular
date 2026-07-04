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
# Arquivo temporario em vez de "process substitution" (<(...)) - a sintaxe
# <(...) nao funciona de forma confiavel no Git Bash/MSYS no Windows; um
# arquivo temporario funciona igual em Linux, Mac e Windows.
#
# keyUsage/extendedKeyUsage sao obrigatorios aqui: sem eles, OpenSSL mais
# novo (3.5+, ex. no Raspberry Pi) rejeita silenciosamente o certificado
# na verificacao mTLS (handshake completa do lado do cliente, mas o
# servidor derruba a conexao sem log nenhum) - descoberto testando contra
# o Pi com OpenSSL 3.5.6 enquanto o notebook (OpenSSL 3.0.13) aceitava sem
# reclamar. Sao a extensao "certa" de qualquer forma, nao so um workaround.
printf "subjectAltName=IP:%s\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth" "$IP_SERVIDOR" > server_ext.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -sha256 -out server.crt -extfile server_ext.cnf
rm -f server_ext.cnf

echo ">> [3/3] Gerando o certificado do CLIENTE (notebook)..."
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout client.key -out client.csr -subj "/CN=gateway-client"
printf "keyUsage=digitalSignature\nextendedKeyUsage=clientAuth" > client_ext.cnf
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -sha256 -out client.crt -extfile client_ext.cnf
rm -f client_ext.cnf

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
