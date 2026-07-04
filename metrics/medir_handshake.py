"""
Medidor de handshake TLS/mTLS isolado - ETAPA 3 (RQ2).
Roda NO NOTEBOOK, contra um servidor (REST na porta 8000 ou gRPC na 50051)
ja rodando com --seguranca tls ou mtls. Mede so o tempo de conectar + fazer
o handshake TLS, SEM enviar nenhum dado de aplicacao - isola o custo
criptografico do resto da latencia (que os clientes de carga ja medem).

E agnostico de protocolo: a mesma medicao serve tanto pro servidor REST
(porta 8000) quanto pro gRPC (porta 50051), pois os dois usam TLS por baixo
com os mesmos certificados. Nao negocia ALPN (h2/http1.1) de proposito -
isso e uma simplificacao: o que queremos comparar e o custo tls vs mtls,
e essa diferenca nao muda com ALPN presente ou nao (afeta os dois modos
igualmente).

Executar (com o servidor alvo ja rodando em --seguranca tls ou mtls):
    python3 medir_handshake.py 192.168.50.1 8000 --seguranca tls
    python3 medir_handshake.py 192.168.50.1 50051 --seguranca mtls
"""
import argparse
import csv
import socket
import ssl
import statistics
import time
from pathlib import Path

_PADRAO_PKI = Path(__file__).resolve().parent.parent / "pki-scripts" / "pki"
N_HANDSHAKES = 50


def montar_contexto(seguranca: str, pki: Path) -> ssl.SSLContext:
    ca_crt = pki / "ca.crt"
    if not ca_crt.exists():
        raise FileNotFoundError(f"ca.crt nao encontrado em {pki}")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=str(ca_crt))
    if seguranca == "mtls":
        client_crt = pki / "client.crt"
        client_key = pki / "client.key"
        if not client_crt.exists() or not client_key.exists():
            raise FileNotFoundError(f"client.crt/client.key nao encontrados em {pki}")
        ctx.load_cert_chain(certfile=str(client_crt), keyfile=str(client_key))
    return ctx


def medir_um_handshake(host: str, porta: int, contexto: ssl.SSLContext) -> float:
    inicio = time.perf_counter()
    with socket.create_connection((host, porta), timeout=10) as sock:
        with contexto.wrap_socket(sock, server_hostname=host):
            pass  # conexao + handshake ja concluidos aqui; nao enviamos nada
    return (time.perf_counter() - inicio) * 1000


def main():
    parser = argparse.ArgumentParser(description="Medidor isolado de handshake TLS/mTLS")
    parser.add_argument("ip", help="IP do servidor (Raspberry Pi)")
    parser.add_argument("porta", type=int, help="Porta do servidor (8000=REST, 50051=gRPC)")
    parser.add_argument("--seguranca", choices=["tls", "mtls"], required=True)
    parser.add_argument("--pki", default=None, help="Pasta com os certificados")
    parser.add_argument("-n", "--repeticoes", type=int, default=N_HANDSHAKES)
    args = parser.parse_args()

    pki_dir = Path(args.pki) if args.pki else _PADRAO_PKI
    try:
        contexto = montar_contexto(args.seguranca, pki_dir)
    except FileNotFoundError as e:
        print(e)
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        return

    print(f">> Medindo {args.repeticoes} handshakes [{args.seguranca}] contra {args.ip}:{args.porta}")
    tempos = []
    for i in range(args.repeticoes):
        try:
            tempos.append(medir_um_handshake(args.ip, args.porta, contexto))
        except (OSError, ssl.SSLError) as e:
            print(f"  erro na tentativa {i}: {e}")
            return

    tempos.sort()
    p50 = statistics.median(tempos)
    p95 = tempos[int(len(tempos) * 0.95) - 1]
    p99 = tempos[int(len(tempos) * 0.99) - 1]
    print("\n=== RESULTADO handshake (ms) ===")
    print(f"  amostras: {len(tempos)}")
    print(f"  P50: {p50:.2f} ms")
    print(f"  P95: {p95:.2f} ms")
    print(f"  P99: {p99:.2f} ms")
    print(f"  media: {statistics.mean(tempos):.2f} ms")

    nome_saida = f"handshake_{args.seguranca}_porta{args.porta}.csv"
    with open(nome_saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["indice", "handshake_ms"])
        for idx, val in enumerate(tempos):
            w.writerow([idx, f"{val:.3f}"])
    print(f"\n  tempos brutos salvos em {nome_saida}")


if __name__ == "__main__":
    main()
