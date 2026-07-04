"""
Cliente de carga gRPC - ETAPA 2.
Roda NO NOTEBOOK. Le o CSV e envia cada linha via gRPC, medindo latencia.

ANTES de rodar: compile o .proto (proto/compilar_proto.sh) - isso ja coloca
telemetria_pb2.py e telemetria_pb2_grpc.py nesta pasta.

Executar (de qualquer diretorio):
    python3 cliente_grpc.py 192.168.50.1
    python3 cliente_grpc.py 192.168.50.1 ../data/telemetria_real.csv
(2o argumento e opcional - caminho do CSV; sem ele usa exemplo_telemetria.csv)
"""
import sys
import csv
import time
import statistics
from pathlib import Path
import grpc
import telemetria_pb2
import telemetria_pb2_grpc

IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.50.1"
# Caminho padrao resolvido a partir da localizacao deste arquivo, nao do
# diretorio de onde o script e chamado (ver mesma nota em cliente_carga.py).
_PADRAO_CSV = Path(__file__).resolve().parent.parent / "data" / "exemplo_telemetria.csv"
ARQUIVO_CSV = sys.argv[2] if len(sys.argv) > 2 else str(_PADRAO_CSV)
N_REQUISICOES = 1000  # Tabela 5 do artigo (cenario C1)
WARMUP = 100          # Tabela 5 do artigo (cenario C1)


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def main():
    try:
        with open(ARQUIVO_CSV, newline="", encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"CSV nao encontrado em: {ARQUIVO_CSV}")
        print("Passe o caminho como 2o argumento: python3 cliente_grpc.py <IP> <caminho_csv>")
        return
    if not linhas:
        print(f"CSV vazio. Verifique o arquivo em {ARQUIVO_CSV}")
        return

    print(f">> Enviando {N_REQUISICOES} requisicoes gRPC para {IP}:50051")
    canal = grpc.insecure_channel(f"{IP}:50051")
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
    with open("latencias_grpc_etapa2.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["indice", "latencia_ms"])
        for i, v in enumerate(latencias):
            w.writerow([i, f"{v:.3f}"])
    print("  salvo em latencias_grpc_etapa2.csv")


if __name__ == "__main__":
    main()
