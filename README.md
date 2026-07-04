# Segurança, Resiliência e Desempenho de Protocolos de Comunicação em Gateways Veiculares Embarcados

> Estudo experimental comparativo entre **REST/JSON** e **gRPC/Protocol Buffers**, sob três níveis de segurança de transporte (**sem TLS · TLS · mTLS**) e conectividade móvel instável, executado em hardware embarcado real — **Raspberry Pi 3B (1 GB RAM)**.

**Status:** proposta de pesquisa · fase experimental inicial (Etapa 1)
**Contexto:** proposta de artigo — disciplina TESC-NCS 2026/1

---

## Contexto

Frotas de veículos comerciais e de emergência dependem de *gateways* embarcados para transmitir telemetria crítica (OBD-II/CAN) por redes móveis sujeitas a instabilidade. Nesses dispositivos — ARM de baixo consumo, RAM limitada, sem refrigeração ativa — a escolha do protocolo de comunicação impacta diretamente o desempenho, o consumo de recursos, o custo criptográfico da autenticação mútua (mTLS) e a superfície de ataque na camada de aplicação (L7).

Este repositório contém o código, os *schemas* e os dados do benchmark que quantifica esse impacto de forma empírica, em hardware real, combinando variáveis que a literatura até hoje só estudou isoladamente: hardware ARM restrito, mTLS como variável experimental, ataques DoS L7 e múltiplos perfis de rede móvel.

## Perguntas de pesquisa

- **RQ1** — Em Raspberry Pi 3B sob redes móveis simuladas, o gRPC/Protobuf apresenta latência (P50/P95/P99) inferior ao REST/JSON para payloads OBD-II?
- **RQ2** — Qual o overhead de latência e CPU introduzido pelo mTLS frente ao TLS unilateral, por protocolo?
- **RQ3** — Sob ataques DoS L7 (JSON Bomb e pacotes malformados), qual protocolo degrada menos CPU/RAM e rejeita mais rápido os payloads inválidos?
- **RQ4** — Qual combinação protocolo + segurança atende simultaneamente mTLS, latência P95 < 500 ms e CPU < 60% para telemetria veicular crítica?

## Roadmap experimental

O experimento é construído em fatias verificáveis — cada etapa valida uma variável antes de somar a próxima.

- [x] **Etapa 1 — Esqueleto** · REST + coleta de CPU/RAM ponta a ponta *(código pronto; validação em hardware em andamento)*
- [x] **Etapa 2 — gRPC** · segundo protocolo, mesma telemetria em formato binário *(código pronto; validar após a Etapa 1)*
- [ ] **Etapa 3 — Segurança** · TLS e mTLS (com medição isolada do handshake — RQ2)
- [ ] **Etapa 4 — Rede** · perfis 3G/4G/LTE via `tc netem`
- [ ] **Etapa 5 — Ataques L7** · JSON Bomb, pacote malformado e pior caso combinado (C3/C4/C5)
- [ ] **Etapa 6 — Matriz** · orquestrador das combinações (protocolo × segurança × rede × payload), 5 rodadas
- [ ] **Etapa 7 — Estatística** · SciPy (Shapiro-Wilk · Mann-Whitney U · Bonferroni) e geração de tabelas/gráficos

## Estrutura do repositório

```
├── servers/        # servidor REST (servidor gRPC entra na Etapa 2)
│   └── rest_server.py
├── client/         # cliente de carga / gerador de requisições
│   └── cliente_carga.py
├── metrics/        # coleta de CPU e RAM no gateway (Raspberry Pi)
│   └── coletor_recursos.py
├── data/           # telemetria de exemplo (dados reais entram na Etapa 1+)
│   └── exemplo_telemetria.csv
├── requirements.txt
├── .gitignore
└── README.md
```

Pastas futuras: `proto/` (schemas Protobuf), `pki-scripts/` (geração da PKI — **sem** certificados reais), `netem/` (perfis de rede), `analise/` (estatística).

## Como executar (Etapa 1)

Topologia: **Raspberry Pi = servidor**, **notebook = cliente**, ligados por cabo Ethernet.

1. Definir IPs fixos e testar (`ping`) entre as duas máquinas.
2. `pip install -r requirements.txt` nas duas.
3. No Pi: coletor (`nice -n 10 python3 metrics/coletor_recursos.py`) e servidor (`python3 servers/rest_server.py`).
4. No notebook: `python3 client/cliente_carga.py <IP_DO_PI>`.

**Critério de sucesso:** saída de `latencias_etapa1.csv` (percentis) e `recursos_pi.csv` (CPU/RAM). Instruções detalhadas nos comentários de cada script.

## Reprodutibilidade

Este projeto adota reprodutibilidade como requisito (REQ-05): código, *schemas* e dados brutos ficam disponíveis publicamente. Certificados e chaves privadas **nunca** são versionados (ver `.gitignore`). O dataset final de telemetria será disponibilizado em repositório de dados aberto (Zenodo) na fase de resultados.

## Autores

- Alessandro Silva
- Emerson Amancio

Universidade do Estado de Santa Catarina (UDESC) — Joinville/SC, Brasil.

## Uso de IA

Ferramentas de IA (Claude, Anthropic) foram utilizadas em apoio à revisão crítica, estruturação e refinamento de texto e código. Todas as decisões de conteúdo, escolhas metodológicas e o código foram revisados e validados pelos autores. Nenhuma ferramenta de IA foi usada para gerar dados experimentais ou referências bibliográficas.

## Licença

A definir.
