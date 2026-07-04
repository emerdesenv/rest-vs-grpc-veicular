#!/bin/bash
# Compila telemetria.proto -> gera os modulos Python do gRPC e ja os coloca
# nas pastas servers/ e client/. Rode UMA vez (e de novo se mudar o .proto).
#
# Requer:  pip install grpcio-tools
# Uso:     bash compilar_proto.sh   (rodando de dentro da pasta proto/)
set -e

echo ">> Compilando para servers/ ..."
python3 -m grpc_tools.protoc -I. --python_out=../servers --grpc_python_out=../servers telemetria.proto

echo ">> Compilando para client/ ..."
python3 -m grpc_tools.protoc -I. --python_out=../client --grpc_python_out=../client telemetria.proto

echo ">> Pronto. Gerados telemetria_pb2.py e telemetria_pb2_grpc.py em servers/ e client/."
