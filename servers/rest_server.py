"""
Servidor REST de telemetria - ETAPA 1 (sem seguranca).
Roda NO RASPBERRY PI. Recebe telemetria em JSON, desserializa e responde.
Executar no Pi:  python3 rest_server.py
"""
from fastapi import FastAPI, Request
import uvicorn

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
    # host 0.0.0.0 = aceita conexoes de fora (do notebook, pelo cabo)
    print(">> Servidor REST ouvindo na porta 8000. Ctrl+C para parar.")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
