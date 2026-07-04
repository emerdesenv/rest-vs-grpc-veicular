"""
Cliente de carga - ETAPA 1.
Roda NO NOTEBOOK. Le o CSV de telemetria e envia cada linha como uma
requisicao REST para o Pi, medindo a latencia de cada envio.

Executar (de qualquer diretorio):
    python3 cliente_carga.py 192.168.50.1
    python3 cliente_carga.py 192.168.50.1 ../data/telemetria_real.csv
(troque o IP pelo IP do Raspberry Pi; o 2o argumento e opcional - caminho
do CSV. Sem ele, usa data/exemplo_telemetria.csv por padrao.)
"""
import sys
import csv
import time
import statistics
from pathlib import Path
import httpx

# --- configuracao ---
IP_SERVIDOR = sys.argv[1] if len(sys.argv) > 1 else "192.168.50.1"
PORTA = 8000
# Caminho padrao resolvido a partir da localizacao deste arquivo (nao do
# diretorio de onde o script e chamado) - assim funciona rodando tanto de
# dentro de client/ quanto da raiz do repo (python3 client/cliente_carga.py).
_PADRAO_CSV = Path(__file__).resolve().parent.parent / "data" / "exemplo_telemetria.csv"
ARQUIVO_CSV = sys.argv[2] if len(sys.argv) > 2 else str(_PADRAO_CSV)
N_REQUISICOES = 1000  # quantas mensagens enviar (Tabela 5 do artigo, cenario C1)
WARMUP = 100          # primeiras N descartadas do calculo (Tabela 5 do artigo)

URL = f"http://{IP_SERVIDOR}:{PORTA}/telemetria"


def carregar_telemetria(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    try:
        linhas = carregar_telemetria(ARQUIVO_CSV)
    except FileNotFoundError:
        print(f"CSV nao encontrado em: {ARQUIVO_CSV}")
        print("Passe o caminho como 2o argumento: python3 cliente_carga.py <IP> <caminho_csv>")
        return
    if not linhas:
        print(f"CSV vazio. Verifique o arquivo em {ARQUIVO_CSV}")
        return

    print(f">> Enviando {N_REQUISICOES} requisicoes para {URL}")
    latencias = []
    # http2=True so tem efeito real a partir da Etapa 3 (TLS): sem TLS nao ha
    # ALPN para negociar HTTP/2, e o httpx nao suporta h2c. Ver nota em
    # servers/rest_server.py. Deixado ligado aqui para nao precisar mexer
    # neste arquivo de novo quando a Etapa 3 chegar.
    with httpx.Client(timeout=10.0, http2=True) as cliente:
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
