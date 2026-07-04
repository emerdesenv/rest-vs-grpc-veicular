# Segurança, Resiliência e Desempenho de Protocolos de Comunicação em Gateways Veiculares Embarcados

> Estudo experimental comparativo entre **REST/JSON** e **gRPC/Protocol Buffers**, sob três níveis de segurança de transporte (**sem TLS · TLS · mTLS**) e conectividade móvel instável, executado em hardware embarcado real — **Raspberry Pi 3B (1 GB RAM)**.

**Status:** proposta de pesquisa · fase experimental inicial (Etapa 1)
**Contexto:** proposta de artigo — disciplina TESC-NCS 2026/1

---

## Em termos simples

Imagine um caminhão, ônibus ou viatura de emergência mandando continuamente, pela
internet do celular, dados do próprio veículo (velocidade, temperatura do motor,
localização) para uma central. Existem duas formas comuns de "empacotar" e enviar
esse tipo de dado entre computadores: uma mais antiga e universal (**REST/JSON** — a
mesma base por trás da maioria dos sites) e uma mais nova e compacta (**gRPC** — usada
por empresas como o Google).

Este projeto testa, num computador pequeno e barato de verdade (**Raspberry Pi**, do
tipo usado em equipamentos embarcados reais — não é simulação em nuvem nem em notebook
potente), qual das duas formas funciona melhor quando:

- **a internet do carro está ruim** (sinal de celular instável, como numa rodovia);
- **é preciso adicionar segurança** para garantir que ninguém finja ser o carro nem
  leia os dados em trânsito (isso se chama **mTLS** — uma trava que exige que os dois
  lados, veículo e central, se identifiquem com um "documento" digital antes de
  conversar);
- **alguém tenta atacar o sistema de propósito**, mandando dados malformados pra ver
  qual dos dois jeitos aguenta mais sem travar ou consumir toda a memória do
  computador de bordo.

O teste roda em duas máquinas de verdade ligadas por cabo: o Raspberry Pi faz o papel
do computador de bordo do veículo, e um notebook simula a central que recebe os
dados. O resultado é um conjunto de números medidos no hardware real (não estimados)
que ajuda a responder qual tecnologia é mais indicada para esse tipo de sistema
crítico. As seções técnicas abaixo (Contexto, Perguntas de pesquisa) são a versão
formal desse mesmo objetivo, para quem já conhece os termos.

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
├── servers/                  # servidores REST e gRPC (rodam no Pi)
│   ├── rest_server.py
│   └── grpc_server.py
├── client/                   # clientes de carga / geradores de requisições
│   ├── cliente_carga.py      # REST
│   └── cliente_grpc.py       # gRPC
├── metrics/                  # coleta de CPU e RAM no gateway
│   └── coletor_recursos.py
├── proto/                    # schema Protobuf + compilador
│   ├── telemetria.proto
│   └── compilar_proto.sh
├── pki-scripts/              # geração da PKI para mTLS (sem certificados reais)
│   └── gerar_pki.sh
├── data/                     # telemetria de exemplo + coletor OBD-II
│   ├── exemplo_telemetria.csv
│   └── coletar_obd.py
├── requirements.txt          # dependências da Etapa 1 (REST)
├── requirements-etapa2.txt   # dependências da Etapa 2 (gRPC)
├── ROTEIRO_DO_DIA.md         # roteiro da sessão de testes
├── TUTORIAL_CSV_E_PKI.md     # como gerar o CSV real e a PKI
├── .gitignore
└── README.md
```

Pastas futuras: `netem/` (perfis de rede), `analise/` (estatística).

## Documentação

- **`ROTEIRO_DO_DIA.md`** — sequência completa da sessão de testes, passo a passo.
- **`TUTORIAL_CSV_E_PKI.md`** — como gerar o CSV de telemetria real (OBD-II) e a PKI do mTLS.

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