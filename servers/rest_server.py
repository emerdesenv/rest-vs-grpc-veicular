"""
Servidor REST de telemetria - ETAPA 1 (sem seguranca).
Roda NO RASPBERRY PI. Recebe telemetria em JSON, desserializa e responde.
Executar no Pi:  python3 rest_server.py

Usa Hypercorn (nao uvicorn) como servidor ASGI: uvicorn so fala HTTP/1.1,
e o artigo (Secao 2.2) exige paridade de transporte HTTP/2 com o gRPC.

IMPORTANTE - a paridade HTTP/2 so vale a partir da Etapa 3 (TLS/mTLS):
sem TLS nao ha ALPN para negociar HTTP/2, e o httpx (cliente) nao suporta
h2c (HTTP/2 em texto claro). Entao nesta Etapa 1/2, o REST roda em HTTP/1.1
de fato, enquanto o gRPC ja usa framing HTTP/2 nativo mesmo sem TLS - essa
assimetria e uma ressalva do cenario "sem seguranca" e precisa ficar
documentada no artigo. A partir da Etapa 3, com certfile/keyfile
configurados abaixo, o Hypercorn negocia HTTP/2 via ALPN automaticamente
e o cliente (http2=True em cliente_carga.py) passa a falar HTTP/2 de fato.
"""
import asyncio
from fastapi import FastAPI, Request
from hypercorn.asyncio import serve
from hypercorn.config import Config

app = FastAPI()

# contador simples para acompanhar quantas mensagens chegaram
contador = {"recebidas": 0}


@app.post("/telemetria")
async def receber_telemetria(request: Request):
    # aqui acontece a desserializacao do JSON (o "parsing" que queremos medir)
    dados = await request.json()
    contador["recebidas"] += 1
    return {"ok": True, "campos": len(dados), "total": contador["recebidas"]}


@app.get("/status")
async def status():
    return {"servidor": "no ar", "recebidas": contador["recebidas"]}


if __name__ == "__main__":
    config = Config()
    config.bind = ["0.0.0.0:8000"]  # aceita conexoes de fora (do notebook, pelo cabo)
    config.loglevel = "warning"
    # Etapa 3: descomentar e apontar para a PKI (pki-scripts/gerar_pki.sh)
    # config.certfile = "../pki/server.crt"
    # config.keyfile = "../pki/server.key"
    print(">> Servidor REST (Hypercorn) ouvindo na porta 8000. Ctrl+C para parar.")
    asyncio.run(serve(app, config))
