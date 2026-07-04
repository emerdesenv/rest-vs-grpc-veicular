"""
Cliente de carga gRPC - ETAPA 2.
Roda NO NOTEBOOK. Le o CSV e envia cada linha via gRPC, medindo latencia.

ANTES de rodar: compile o .proto (proto/compilar_proto.sh) - isso ja coloca
telemetria_pb2.py e telemetria_pb2_grpc.py nesta pasta.

Executar:  python3 cliente_grpc.py 192.168.50.1
"""
import sys
import csv
import time
import statistics
import grpc
import telemetria_pb2
import telemetria_pb2_grpc

IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.50.1"
ARQUIVO_CSV = "../data/exemplo_telemetria.csv"
N_REQUISICOES = 100
WARMUP = 10


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def main():
    with open(ARQUIVO_CSV, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        print("CSV vazio.")
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
        stub.Enviar(amostra)
        fim = time.perf_counter()
        if i >= WARMUP:
            latencias.append((fim - inicio) * 1000)

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
