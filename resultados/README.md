# Resultados — evidência real capturada em hardware

Todos os arquivos aqui vêm de execuções reais no Raspberry Pi (servidor) e
no notebook (cliente), ligados por cabo Ethernet — não são dados
simulados/sintéticos. Cada subpasta corresponde a uma etapa do
[roadmap experimental](../README.md#roadmap-experimental).

## `etapa1_rest/` — Etapa 1, sem segurança, sem rede degradada

| Arquivo | Conteúdo |
|---|---|
| `latencias_etapa1.csv` | Latência REST (P50 4.18-4.48 ms, P95 4.55-4.76 ms, P99 5.09-5.30 ms) |
| `recursos_pi.csv` | CPU/RAM do Pi durante o teste (pico de CPU 26.5%) |
| `capturas/` | 10 screenshots dos terminais (Pi + notebook) durante a captura |

## `etapa2_grpc/` — Etapa 2, sem segurança, sem rede degradada

| Arquivo | Conteúdo |
|---|---|
| `latencias_grpc_etapa2.csv` | Latência gRPC (P50 2.26 ms, P95 2.75 ms, P99 2.94 ms) |
| `recursos_pi_grpc.csv` | CPU/RAM do Pi durante o teste (pico de CPU 29.2%) |
| `capturas/` | 7 screenshots dos terminais + 7 fotos físicas do Pi (`htop` rodando `grpc_server.py`, tiradas pelo Alessandro) + 1 vídeo |

**Achado (RQ1):** gRPC consistentemente mais rápido que REST em todos os
percentis, mesma rede cabeada, sem segurança.

> **Nota de transparência:** `latencias_grpc_etapa2.csv` foi corrigido
> depois de uma reconciliação com um backup manual do usuário
> (`Documents/METRICAS_UDESC`) — a versão que ficou aqui num primeiro
> momento era de um teste local em loopback (Windows, ~0.4ms), sobrescrita
> por engano durante o desenvolvimento da Etapa 3, não o teste real do Pi.
> O valor correto (2.26ms) é o que está documentado acima e é o que foi
> reportado originalmente durante a sessão de captura.

## `etapa3_seguranca/` — Etapa 3, TLS e mTLS (RQ2)

| Arquivo | Conteúdo |
|---|---|
| `latencias_etapa3_tls.csv` / `latencias_etapa3_mtls.csv` | Latência REST em TLS unilateral (P50 7.48ms) e mTLS (P50 7.45ms) |
| `latencias_grpc_etapa3_tls.csv` / `latencias_grpc_etapa3_mtls.csv` | Latência gRPC em TLS (P50 2.40ms) e mTLS (P50 2.38ms) |
| `recursos_pi_tls.csv` / `recursos_pi_mtls.csv` | CPU/RAM REST (pico 26.5-26.8%) |
| `recursos_pi_grpc_tls.csv` / `recursos_pi_grpc_mtls.csv` | CPU/RAM gRPC (pico 27.1-31.3%) |
| `handshake_tls_porta8000.csv` / `handshake_mtls_porta8000.csv` | Handshake isolado REST (P50 ~31ms tls / ~32ms mtls) |
| `handshake_tls_porta50051.csv` / `handshake_mtls_porta50051.csv` | Handshake isolado gRPC (P50 ~32ms tls / ~32ms mtls) |
| `capturas/` | 10 screenshots dos terminais + 10 fotos físicas do Pi (`htop` durante REST mTLS e gRPC TLS/mTLS, tiradas pelo Alessandro) |

**Achado (RQ2):** no REST, ligar TLS custa ~+3.3ms de latência sobre o
baseline sem segurança; a autenticação mútua (mTLS) em cima do TLS não
soma overhead perceptível — nem na latência de requisição nem no
handshake isolado. No gRPC, os três níveis de segurança ficam próximos
entre si (implementação BoringSSL/C aparenta ser mais barata que a
pilha Python/OpenSSL do REST). CPU não mostrou diferença relevante entre
níveis de segurança, em nenhum dos dois protocolos.

## `etapa4_rede/` — Etapa 4, perfis de rede móvel (`tc netem`)

| Arquivo | Conteúdo |
|---|---|
| `latencias_etapa1_3g.csv` | Latência REST sob perfil 3G (P50 118.6ms, P99 594-596ms) |
| `latencias_etapa1_4g.csv` | Latência REST sob perfil 4G (P50 46.1ms) |
| `capturas/` | 3 screenshots (aplicação dos perfis 3G e 4G no Pi) |

**Achado:** perfis aplicados via `netem/aplicar_perfil.sh` na interface do
Pi degradam a latência na direção esperada (3G >> 4G >> sem perfil), com o
P99 do 3G refletindo o efeito da perda de pacotes (2%) configurada.
Perfil LTE não foi testado com captura de latência dedicada.

## `etapa5_ataques/` — Etapa 5, ataques L7 (RQ3), condição oficial do artigo (mTLS + rede 3G)

| Arquivo | Cenário |
|---|---|
| `ataque_rest_jsonbomb_3g_mtls.csv` | **C3** REST — JSON Bomb (profundidade 100): 214-202/214 aceito |
| `ataque_rest_malformado_3g_mtls.csv` | **C4** REST — bytes aleatórios: rejeitado (HTTP 500, sem tratamento de erro) |
| `ataque_grpc_jsonbomb_3g_mtls.csv` | **C3** gRPC — JSON Bomb: rejeitado rápido (framing HTTP/2 inválido) |
| `ataque_grpc_malformado_3g_mtls.csv` | **C4** gRPC — bytes aleatórios: rejeitado rápido |
| `recursos_pi_ataque_3g_mtls.csv` | CPU/RAM durante C3 REST (pico 26.6%) |
| `recursos_pi_c4_rest.csv` | CPU/RAM durante C4 REST (pico 26.1%) |
| `recursos_pi_c3c4_grpc.csv` | CPU/RAM durante C3+C4 gRPC (pico 26.4%) |
| `recursos_pi_c5.csv` | **C5** — CPU/RAM com C3+C4 simultâneos contra REST (pico 26.0%, sem amplificação) |
| `supervisor_eventos.csv` | Log do `metrics/supervisor.sh` durante o C5 — nenhuma linha `caiu_reiniciando`, ou seja, o servidor não caiu |
| `capturas/` | 1 screenshot (aplicação do perfil 3G + coletor para o ataque) |

**Achado (RQ3):** na profundidade 100 especificada pelo artigo, o JSON
Bomb **não estressa** CPU/RAM do REST de forma significativa, mesmo sob
mTLS + rede 3G. Payload malformado é rejeitado (HTTP 500) sem tratamento
de erro no código, mas sem derrubar o serviço. gRPC rejeita ambos os
ataques rapidamente graças ao contrato rígido de schema. O cenário
combinado (C5) não mostrou efeito de amplificação/ruptura nessa
configuração — o mecanismo de reinício automático (`supervisor.sh`) foi
validado separadamente (recuperação em ~3.2s num teste controlado), mas
não chegou a ser acionado durante o C5 real porque o servidor não caiu.

Uma investigação à parte (não documentada em CSV, registrada na condução
do experimento) achou o **ponto de quebra real do REST por profundidade
de aninhamento**: entre profundidade 950-980 (Python 3.11) e 5000-10000
(Python 3.13 do Pi) o parser passa a rejeitar com `RecursionError` (HTTP
500) - nunca com crash/OOM, em nenhuma profundidade testada (até 50000).
Isso é mais informativo que a hipótese original do artigo (exaustão de
RAM): o limite de recursão do Python age como proteção involuntária muito
antes de qualquer pressão de memória real aparecer.

## `exploratorio/`

**Não é evidência oficial** — ver `exploratorio/AVISO.md`.
