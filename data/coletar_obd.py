"""
Coletor de telemetria OBD-II -> CSV
Roda na maquina com o adaptador OBD-II conectado ao veiculo (chave ligada).
Le PIDs padrao a cada intervalo e grava em telemetria_real.csv.

Uso:
    python3 coletar_obd.py                 # tenta detectar a porta sozinho
    python3 coletar_obd.py /dev/ttyUSB0    # porta manual (adaptador USB)
    python3 coletar_obd.py /dev/rfcomm0    # porta manual (adaptador Bluetooth)

Parar com Ctrl+C -> fecha o CSV com o que ja coletou.

Requer:  pip install obd
"""
import sys
import csv
import time
from datetime import datetime
import obd

INTERVALO = 1.0            # segundos entre leituras
ARQUIVO = "telemetria_real.csv"

# PIDs OBD-II -> colunas do CSV.
# (GPS NAO e um PID OBD-II: latitude/longitude vem de outra fonte e entram depois.)
PIDS = {
    "velocidade":     obd.commands.SPEED,          # km/h
    "rpm":            obd.commands.RPM,             # rotacoes/min
    "temp_motor":     obd.commands.COOLANT_TEMP,    # graus C
    "carga_motor":    obd.commands.ENGINE_LOAD,     # %
    "acelerador":     obd.commands.THROTTLE_POS,    # %
    "tensao_bateria": obd.commands.ELM_VOLTAGE,     # V (vem do proprio adaptador)
}


def valor(resposta):
    """Extrai so o numero da resposta (sem a unidade)."""
    if resposta is None or resposta.is_null():
        return ""
    v = resposta.value
    return getattr(v, "magnitude", v)


def main():
    porta = sys.argv[1] if len(sys.argv) > 1 else None
    print(">> Conectando ao adaptador OBD-II...")
    conexao = obd.OBD(porta) if porta else obd.OBD()

    if not conexao.is_connected():
        print("ERRO: nao conectou. Confira:")
        print("  - adaptador OBD-II bem encaixado e chave do carro ligada;")
        print("  - a porta certa (tente:  python3 coletar_obd.py /dev/ttyUSB0);")
        print("  - permissao da porta (pode precisar de 'sudo' ou do grupo dialout).")
        return

    print(f">> Conectado em {conexao.port_name()}. Coletando a cada {INTERVALO}s. Ctrl+C para parar.")
    colunas = ["timestamp"] + list(PIDS.keys())
    with open(ARQUIVO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        try:
            while True:
                linha = {"timestamp": datetime.now().isoformat(timespec="seconds")}
                for nome, cmd in PIDS.items():
                    linha[nome] = valor(conexao.query(cmd))
                w.writerow(linha)
                f.flush()
                print("  " + " | ".join(f"{c}={linha[c]}" for c in colunas))
                time.sleep(INTERVALO)
        except KeyboardInterrupt:
            print(f"\n>> Parado. Telemetria salva em {ARQUIVO}")


if __name__ == "__main__":
    main()
