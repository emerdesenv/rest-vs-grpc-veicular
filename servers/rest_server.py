"""
Servidor REST de telemetria - ETAPA 1/3 (sem seguranca / TLS / mTLS).
Roda NO RASPBERRY PI. Recebe telemetria em JSON, desserializa e responde.

Executar no Pi:
    python3 rest_server.py                       # sem seguranca (Etapa 1)
    python3 rest_server.py --seguranca tls        # TLS unilateral (Etapa 3)
    python3 rest_server.py --seguranca mtls       # mTLS (Etapa 3)

Usa Hypercorn (nao uvicorn) como servidor ASGI: uvicorn so fala HTTP/1.1,
e o artigo (Secao 2.2) exige paridade de transporte HTTP/2 com o gRPC.

IMPORTANTE - a paridade HTTP/2 so vale a partir de --seguranca tls/mtls:
sem TLS nao ha ALPN para negociar HTTP/2, e o httpx (cliente) nao suporta
h2c (HTTP/2 em texto claro). Entao em --seguranca none, o REST roda em
HTTP/1.1 de fato, enquanto o gRPC ja usa framing HTTP/2 nativo mesmo sem
TLS - essa assimetria e uma ressalva do cenario "sem seguranca" e precisa
ficar documentada no artigo. Com tls/mtls, o Hypercorn negocia HTTP/2 via
ALPN automaticamente e o cliente (http2=True em cliente_carga.py) passa a
falar HTTP/2 de fato.
"""
import argparse
import asyncio
import ssl
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from hypercorn.asyncio import serve
from hypercorn.config import Config

app = FastAPI()


class ConfigCompativel(Config):
    """
    Hypercorn.create_ssl_context() usa ssl.create_default_context(Purpose.CLIENT_AUTH)
    como base. Isolamos (testando asyncio puro vs Hypercorn no mesmo Python/OpenSSL)
    que essa chamada especifica trava silenciosamente o handshake mTLS no OpenSSL
    3.5+ (Raspberry Pi OS / Debian 13) mesmo com um certificado de cliente valido -
    o handshake "termina" do lado do cliente mas o servidor nunca responde. Um
    SSLContext comum com as mesmas configuracoes nao tem esse problema. Esta
    versao reconstroi o contexto do Hypercorn manualmente, trocando so essa parte.
    """

    def create_ssl_context(self):
        if not self.ssl_enabled:
            return None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.set_ciphers(self.ciphers)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.options = ssl.OP_NO_COMPRESSION
        context.set_alpn_protocols(self.alpn_protocols)
        if self.certfile is not None and self.keyfile is not None:
            context.load_cert_chain(
                certfile=self.certfile, keyfile=self.keyfile, password=self.keyfile_password,
            )
        if self.ca_certs is not None:
            context.load_verify_locations(self.ca_certs)
        if self.verify_mode is not None:
            context.verify_mode = self.verify_mode
        if self.verify_flags is not None:
            context.verify_flags = self.verify_flags
        return context

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


def montar_config(seguranca: str, pki: Path, loglevel: str = "warning") -> Config:
    config = ConfigCompativel()
    config.bind = ["0.0.0.0:8000"]  # aceita conexoes de fora (do notebook, pelo cabo)
    config.loglevel = loglevel
    config.accesslog = "-"
    config.errorlog = "-"

    if seguranca == "none":
        return config

    server_crt = pki / "server.crt"
    server_key = pki / "server.key"
    if not server_crt.exists() or not server_key.exists():
        print(f"Certificado/chave do servidor nao encontrados em {pki}")
        print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
        sys.exit(1)
    config.certfile = str(server_crt)
    config.keyfile = str(server_key)

    if seguranca == "mtls":
        ca_crt = pki / "ca.crt"
        if not ca_crt.exists():
            print(f"ca.crt nao encontrado em {pki}")
            print("Gere a PKI primeiro: bash pki-scripts/gerar_pki.sh")
            sys.exit(1)
        config.ca_certs = str(ca_crt)
        config.verify_mode = ssl.CERT_REQUIRED

    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor REST de telemetria")
    parser.add_argument(
        "--seguranca", choices=["none", "tls", "mtls"], default="none",
        help="Nivel de seguranca de transporte (padrao: none)",
    )
    parser.add_argument(
        "--pki", default=None,
        help="Pasta com os certificados (padrao: pki-scripts/pki/ na raiz do repo)",
    )
    parser.add_argument("--loglevel", default="warning", help="debug/info/warning/error")
    args = parser.parse_args()

    pki_dir = Path(args.pki) if args.pki else Path(__file__).resolve().parent.parent / "pki-scripts" / "pki"
    config = montar_config(args.seguranca, pki_dir, args.loglevel)

    protocolo = {"none": "http", "tls": "https", "mtls": "https (mTLS)"}[args.seguranca]
    print(f">> Servidor REST (Hypercorn) ouvindo na porta 8000 [{protocolo}]. Ctrl+C para parar.")
    asyncio.run(serve(app, config))
