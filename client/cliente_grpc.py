"""
Cliente de carga gRPC - ETAPA 2/3.
Roda NO NOTEBOOK. Le o CSV e envia cada linha via gRPC, medindo latencia.

ANTES de rodar: compile o .proto (proto/compilar_proto.sh) - isso ja coloca
telemetria_pb2.py e telemetria_pb2_grpc.py nesta pasta.

Executar (de qualquer diretorio):
    python3 cliente_grpc.py 192.168.50.1
    python3 cliente_grpc.py 192.168.50.1 ../data/telemetria_real.csv
    python3 cliente_grpc.py 192.168.50.1 --seguranca tls
    python3 cliente_grpc.py 192.168.50.1 --seguranca mtls --pki ../pki-scripts/pki
    python3 cliente_grpc.py 192.168.50.1 --rede 3g
(2o argumento posicional e opcional - caminho do CSV; sem ele usa exemplo_telemetria.csv.
--rede so nomeia o arquivo de saida - o perfil de rede em si e aplicado no Pi via
netem/aplicar_perfil.sh, antes de rodar este cliente.)
"""
import argparse
import csv
import time
import statistics
from pathlib import Path
import grpc
import telemetria_pb2
import telemetria_pb2_grpc

_PADRAO_CSV = Path(__file__).resolve().parent.parent / "data" / "exemplo_telemetria.csv"
_PADRAO_PKI = Path(__file__).resolve().parent.parent / "pki-scripts" / "pki"
N_REQUISICOES = 1000  # Tabela 5 do artigo (cenario C1)
WARMUP = 100          # Tabela 5 do artigo (cenario C1)

NOME_SAIDA = {
    "none": "latencias_grpc_etapa2.csv",
    "tls": "latencias_grpc_etapa3_tls.csv",
    "mtls": "latencias_grpc_etapa3_mtls.csv",
}


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def montar_canal(ip: str, seguranca: str, pki: Path):
    alvo = f"{ip}:50051"
    if seguranca == "none":
        return grpc.insecure_channel(alvo)

    ca_crt = pki / "ca.crt"
    if not ca_crt.exists():
        raise FileNotFoundError(f"ca.crt nao encontrado em {pki}")

    if seguranca == "tls":
        credenciais = grpc.ssl_channel_credentials(root_certificates=ca_crt.read_bytes())
        return grpc.secure_channel(alvo, credenciais)

    # mtls
    client_crt = pki / "client.crt"
    client_key = pki / "client.key"
    if not client_crt.exists() or not client_key.exists():
        raise FileNotFoundError(f"client.crt/client.key nao encontrados em {pki}")
    credenciais = grpc.ssl_channel_credentials(
        root_certificates=ca_crt.read_bytes(),
        private_key=client_key.read_bytes(),
        certificate_chain=client_crt.read_bytes(),
    )
    return grpc.secure_channel(alvo, credenciais)


def main():
    parser = argparse.ArgumentParser(description="Cliente de carga gRPC")
    parser.add_argument("ip", nargs="?", default="192.168.50.1", help="IP do Raspberry Pi")
    parser.add_argument("csv_path", nargs="?", default=None, help="Caminho do CSV de telemetria")
    parser.add_argument("--seguranca", choices=["none", "tls", "mtls"], default="none")
    parser.add_argument("--pki", default=None, help="Pasta com os certificados")
    parser.add_argument(
        "--rede", choices=["direto", "3g", "4g", "lte"], default="direto",
        help="So para nomear o arquivo de saida - nao aplica o perfil (isso e feito no "
             "Pi via netem/aplicar_perfil.sh).",
    )
    args = parser.parse_args()

    arquivo_csv = args.csv_path or str(_PADRAO_CSV)
    pki_dir = Path(args.pki) if args.pki else _PADRAO_PKI

    try:
        with open(arquivo_csv, newline="", encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"CSV nao encontrado em: {arquivo_csv}")
        print("Passe o caminho como 2o argumento: python3 cliente_grpc.py <IP> <caminho_csv>")
        return
    if not linhas:
        print(f"CSV vazio. Verifique o arquivo em {arquivo_csv}")
        return

    try:
        canal = montar_canal(args.ip, args.seguranca, pki_dir)
    except FileNotFoundError as e:
        print(e)
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        return

    print(f">> Enviando {N_REQUISICOES} requisicoes gRPC para {args.ip}:50051 [seguranca={args.seguranca}, rede={args.rede}]")
    stub = telemetria_pb2_grpc.TelemetriaStub(canal)
    latencias = []
    for i in range(N_REQUISICOES):
        d = linhas[i % len(linhas)]
        amostra = telemetria_pb2.Amostra(
            timestamp=str(d.get("timestamp", "")),
            velocidade=num(d.get("velocidade")),
            rpm=num(d.get("rpm")),
            temp_motor=num(d.get("temp_motor")),
            carga_motor=num(d.get("carga_motor")),
            acelerador=num(d.get("acelerador")),
            tensao_bateria=num(d.get("tensao_bateria")),
            lat=num(d.get("lat")),
            lon=num(d.get("lon")),
        )
        inicio = time.perf_counter()
        try:
            stub.Enviar(amostra)
        except grpc.RpcError as e:
            print(f"  erro na requisicao {i}: {e.code()} - {e.details()}")
            return
        fim = time.perf_counter()
        if i >= WARMUP:
            latencias.append((fim - inicio) * 1000)

    if not latencias:
        print("Nenhuma latencia coletada. Verifique se o servidor esta no ar.")
        return

    latencias.sort()
    print("\n=== RESULTADO gRPC (latencia em ms) ===")
    print(f"  amostras: {len(latencias)}")
    print(f"  P50: {statistics.median(latencias):.2f} ms")
    print(f"  P95: {latencias[int(len(latencias) * 0.95) - 1]:.2f} ms")
    print(f"  P99: {latencias[int(len(latencias) * 0.99) - 1]:.2f} ms")
    nome_saida = NOME_SAIDA[args.seguranca]
    if args.rede != "direto":
        nome_saida = nome_saida.replace(".csv", f"_{args.rede}.csv")
    with open(nome_saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["indice", "latencia_ms"])
        for i, v in enumerate(latencias):
            w.writerow([i, f"{v:.3f}"])
    print(f"  salvo em {nome_saida}")


if __name__ == "__main__":
    main()
