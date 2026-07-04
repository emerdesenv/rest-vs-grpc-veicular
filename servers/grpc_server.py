"""
Servidor gRPC de telemetria - ETAPA 2/3 (sem seguranca / TLS / mTLS).
Roda NO RASPBERRY PI. Recebe telemetria via gRPC/Protobuf e responde.

ANTES de rodar: compile o .proto uma vez (proto/compilar_proto.sh) - isso
gera telemetria_pb2.py e telemetria_pb2_grpc.py nesta pasta.

Executar no Pi:
    python3 grpc_server.py                       # sem seguranca (Etapa 2)
    python3 grpc_server.py --seguranca tls        # TLS unilateral (Etapa 3)
    python3 grpc_server.py --seguranca mtls       # mTLS (Etapa 3)
(So depois que a Etapa 1 - REST - estiver validada.)
"""
import argparse
import sys
from concurrent import futures
from pathlib import Path

import grpc
import telemetria_pb2
import telemetria_pb2_grpc

contador = {"recebidas": 0}


class ServicoTelemetria(telemetria_pb2_grpc.TelemetriaServicer):
    def Enviar(self, request, context):
        # a desserializacao ja aconteceu: 'request' e um objeto tipado
        contador["recebidas"] += 1
        return telemetria_pb2.Confirmacao(ok=True, total=contador["recebidas"])


def montar_credenciais(seguranca: str, pki: Path):
    server_key = pki / "server.key"
    server_crt = pki / "server.crt"
    if not server_key.exists() or not server_crt.exists():
        print(f"Certificado/chave do servidor nao encontrados em {pki}")
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        sys.exit(1)
    chave = server_key.read_bytes()
    certificado = server_crt.read_bytes()

    if seguranca == "tls":
        return grpc.ssl_server_credentials([(chave, certificado)])

    # mtls
    ca_crt = pki / "ca.crt"
    if not ca_crt.exists():
        print(f"ca.crt nao encontrado em {pki}")
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        sys.exit(1)
    return grpc.ssl_server_credentials(
        [(chave, certificado)],
        root_certificates=ca_crt.read_bytes(),
        require_client_auth=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Servidor gRPC de telemetria")
    parser.add_argument(
        "--seguranca", choices=["none", "tls", "mtls"], default="none",
        help="Nivel de seguranca de transporte (padrao: none)",
    )
    parser.add_argument(
        "--pki", default=None,
        help="Pasta com os certificados (padrao: pki-scripts/pki/ na raiz do repo)",
    )
    args = parser.parse_args()

    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    telemetria_pb2_grpc.add_TelemetriaServicer_to_server(ServicoTelemetria(), servidor)

    if args.seguranca == "none":
        servidor.add_insecure_port("0.0.0.0:50051")
    else:
        pki_dir = Path(args.pki) if args.pki else Path(__file__).resolve().parent.parent / "pki-scripts" / "pki"
        credenciais = montar_credenciais(args.seguranca, pki_dir)
        servidor.add_secure_port("0.0.0.0:50051", credenciais)

    servidor.start()
    print(f">> Servidor gRPC ouvindo na porta 50051 [seguranca={args.seguranca}]. Ctrl+C para parar.")
    servidor.wait_for_termination()


if __name__ == "__main__":
    main()
