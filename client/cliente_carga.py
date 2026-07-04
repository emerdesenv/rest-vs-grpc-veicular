"""
Cliente de carga - ETAPA 1.
Roda NO NOTEBOOK. Le o CSV de telemetria e envia cada linha como uma
requisicao REST para o Pi, medindo a latencia de cada envio.

Executar no notebook:  python3 cliente_carga.py 192.168.50.1
(troque o IP pelo IP do Raspberry Pi)
"""
import sys
import csv
import time
import statistics
import httpx

# --- configuracao ---
IP_SERVIDOR = sys.argv[1] if len(sys.argv) > 1 else "192.168.50.1"
PORTA = 8000
ARQUIVO_CSV = "../data/exemplo_telemetria.csv"
N_REQUISICOES = 100   # quantas mensagens enviar
WARMUP = 10           # primeiras N descartadas do calculo (aquecimento)

URL = f"http://{IP_SERVIDOR}:{PORTA}/telemetria"


def carregar_telemetria(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    linhas = carregar_telemetria(ARQUIVO_CSV)
    if not linhas:
        print("CSV vazio. Verifique o arquivo em data/exemplo_telemetria.csv")
        return

    print(f">> Enviando {N_REQUISICOES} requisicoes para {URL}")
    latencias = []
    with httpx.Client(timeout=10.0) as cliente:
        for i in range(N_REQUISICOES):
            payload = linhas[i % len(linhas)]  # reaproveita as linhas em ciclo
            inicio = time.perf_counter()
            try:
                r = cliente.post(URL, json=payload)
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

    with open("latencias_etapa1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["indice", "latencia_ms"])
        for idx, val in enumerate(latencias):
            w.writerow([idx, f"{val:.3f}"])
    print("\n  latencias brutas salvas em latencias_etapa1.csv")


if __name__ == "__main__":
    main()
