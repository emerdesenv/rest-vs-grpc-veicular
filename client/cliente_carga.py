"""
Cliente de carga - ETAPA 1/3.
Roda NO NOTEBOOK. Le o CSV de telemetria e envia cada linha como uma
requisicao REST para o Pi, medindo a latencia de cada envio.

Executar (de qualquer diretorio):
    python3 cliente_carga.py 192.168.50.1
    python3 cliente_carga.py 192.168.50.1 ../data/telemetria_real.csv
    python3 cliente_carga.py 192.168.50.1 --seguranca tls
    python3 cliente_carga.py 192.168.50.1 --seguranca mtls --pki ../pki-scripts/pki
(troque o IP pelo IP do Raspberry Pi; o 2o argumento posicional e opcional -
caminho do CSV. Sem ele, usa data/exemplo_telemetria.csv por padrao.)
"""
import argparse
import csv
import time
import statistics
from pathlib import Path
import httpx

N_REQUISICOES = 1000  # quantas mensagens enviar (Tabela 5 do artigo, cenario C1)
WARMUP = 100          # primeiras N descartadas do calculo (Tabela 5 do artigo)

_PADRAO_CSV = Path(__file__).resolve().parent.parent / "data" / "exemplo_telemetria.csv"
_PADRAO_PKI = Path(__file__).resolve().parent.parent / "pki-scripts" / "pki"

NOME_SAIDA = {
    "none": "latencias_etapa1.csv",
    "tls": "latencias_etapa3_tls.csv",
    "mtls": "latencias_etapa3_mtls.csv",
}


def carregar_telemetria(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def montar_cliente(seguranca: str, pki: Path) -> httpx.Client:
    # http2=True so tem efeito real com TLS: sem TLS nao ha ALPN para
    # negociar HTTP/2, e o httpx nao suporta h2c. Ver nota em
    # servers/rest_server.py.
    if seguranca == "none":
        return httpx.Client(timeout=10.0, http2=True)

    ca_crt = pki / "ca.crt"
    if not ca_crt.exists():
        raise FileNotFoundError(f"ca.crt nao encontrado em {pki}")

    if seguranca == "tls":
        return httpx.Client(timeout=10.0, http2=True, verify=str(ca_crt))

    # mtls
    client_crt = pki / "client.crt"
    client_key = pki / "client.key"
    if not client_crt.exists() or not client_key.exists():
        raise FileNotFoundError(f"client.crt/client.key nao encontrados em {pki}")
    return httpx.Client(
        timeout=10.0, http2=True, verify=str(ca_crt),
        cert=(str(client_crt), str(client_key)),
    )


def main():
    parser = argparse.ArgumentParser(description="Cliente de carga REST")
    parser.add_argument("ip", nargs="?", default="192.168.50.1", help="IP do Raspberry Pi")
    parser.add_argument("csv_path", nargs="?", default=None, help="Caminho do CSV de telemetria")
    parser.add_argument("--seguranca", choices=["none", "tls", "mtls"], default="none")
    parser.add_argument("--pki", default=None, help="Pasta com os certificados")
    args = parser.parse_args()

    arquivo_csv = args.csv_path or str(_PADRAO_CSV)
    pki_dir = Path(args.pki) if args.pki else _PADRAO_PKI
    esquema = "http" if args.seguranca == "none" else "https"
    url = f"{esquema}://{args.ip}:8000/telemetria"

    try:
        linhas = carregar_telemetria(arquivo_csv)
    except FileNotFoundError:
        print(f"CSV nao encontrado em: {arquivo_csv}")
        print("Passe o caminho como 2o argumento: python3 cliente_carga.py <IP> <caminho_csv>")
        return
    if not linhas:
        print(f"CSV vazio. Verifique o arquivo em {arquivo_csv}")
        return

    try:
        cliente_ctx = montar_cliente(args.seguranca, pki_dir)
    except FileNotFoundError as e:
        print(e)
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        return

    print(f">> Enviando {N_REQUISICOES} requisicoes para {url} [seguranca={args.seguranca}]")
    latencias = []
    with cliente_ctx as cliente:
        for i in range(N_REQUISICOES):
            payload = linhas[i % len(linhas)]  # reaproveita as linhas em ciclo
            inicio = time.perf_counter()
            try:
                r = cliente.post(url, json=payload)
            except Exception as e:
                print(f"  erro na requisicao {i}: {e}")
                return
            fim = time.perf_counter()
            if r.status_code != 200:
                print(f"  aviso: requisicao {i} devolveu status {r.status_code}")
                continue
            if i >= WARMUP:
                latencias.append((fim - inicio) * 1000)  # em milissegundos

    if not latencias:
        print("Nenhuma latencia coletada. Verifique se o servidor esta no ar.")
        return

    latencias.sort()
    p50 = statistics.median(latencias)
    p95 = latencias[int(len(latencias) * 0.95) - 1]
    p99 = latencias[int(len(latencias) * 0.99) - 1]
    print("\n=== RESULTADO (latencia em ms) ===")
    print(f"  amostras: {len(latencias)}")
    print(f"  P50 (mediana): {p50:.2f} ms")
    print(f"  P95:           {p95:.2f} ms")
    print(f"  P99:           {p99:.2f} ms")
    print(f"  media:         {statistics.mean(latencias):.2f} ms")

    nome_saida = NOME_SAIDA[args.seguranca]
    with open(nome_saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["indice", "latencia_ms"])
        for idx, val in enumerate(latencias):
            w.writerow([idx, f"{val:.3f}"])
    print(f"\n  latencias brutas salvas em {nome_saida}")


if __name__ == "__main__":
    main()
