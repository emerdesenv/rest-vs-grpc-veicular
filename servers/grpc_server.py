"""
Servidor gRPC de telemetria - ETAPA 2 (sem seguranca).
Roda NO RASPBERRY PI. Recebe telemetria via gRPC/Protobuf e responde.

ANTES de rodar: compile o .proto uma vez (proto/compilar_proto.sh) - isso
gera telemetria_pb2.py e telemetria_pb2_grpc.py nesta pasta.

Executar no Pi:  python3 grpc_server.py
(So depois que a Etapa 1 - REST - estiver validada.)
"""
import grpc
from concurrent import futures
import telemetria_pb2
import telemetria_pb2_grpc

contador = {"recebidas": 0}


class ServicoTelemetria(telemetria_pb2_grpc.TelemetriaServicer):
    def Enviar(self, request, context):
        # a desserializacao ja aconteceu: 'request' e um objeto tipado
        contador["recebidas"] += 1
        return telemetria_pb2.Confirmacao(ok=True, total=contador["recebidas"])


def main():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    telemetria_pb2_grpc.add_TelemetriaServicer_to_server(ServicoTelemetria(), servidor)
    servidor.add_insecure_port("0.0.0.0:50051")
    servidor.start()
    print(">> Servidor gRPC ouvindo na porta 50051. Ctrl+C para parar.")
    servidor.wait_for_termination()


if __name__ == "__main__":
    main()
