"""
Coletor de recursos (CPU e RAM) - roda NO RASPBERRY PI, EM PARALELO ao servidor.
Grava uma amostra a cada 0,5 s num CSV com horario.

Executar no Pi, em OUTRO terminal:  nice -n 10 python3 coletor_recursos.py
Parar com Ctrl+C -> ele fecha o arquivo automaticamente.

(O 'nice -n 10' deixa o coletor com prioridade mais baixa, para ele
 interferir o minimo possivel na medicao do servidor.)
"""
import psutil
import time
import csv
from datetime import datetime

INTERVALO = 0.5  # segundos entre amostras
ARQUIVO = "recursos_pi.csv"


def main():
    print(f">> Coletando CPU/RAM a cada {INTERVALO}s. Ctrl+C para parar.")
    with open(ARQUIVO, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["horario", "cpu_percent", "ram_percent", "ram_usada_mb"])
        psutil.cpu_percent(interval=None)  # 1a leitura vem zerada; descartamos
        try:
            while True:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                w.writerow([
                    datetime.now().isoformat(timespec="milliseconds"),
                    cpu,
                    mem.percent,
                    round(mem.used / (1024 * 1024), 1),
                ])
                f.flush()  # garante os dados no disco mesmo se algo travar
                time.sleep(INTERVALO)
        except KeyboardInterrupt:
            print(f"\n>> Parado. Dados salvos em {ARQUIVO}")


if __name__ == "__main__":
    main()
