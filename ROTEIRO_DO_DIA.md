# Roteiro do dia de teste

**O que estamos testando hoje, em uma frase:** vamos rodar, num Raspberry Pi de
verdade fazendo o papel de computador de bordo, os dois jeitos de mandar dado do
carro (REST e gRPC — ver "Em termos simples" no README) e cronometrar qual é mais
rápido — ainda sem nenhuma camada de segurança extra, só pra confirmar que o
"encanamento" básico funciona de ponta a ponta.

Sequência única da sessão, na ordem. A ideia é fechar a **base** com folga e
avançar só até onde der sem atropelar. Print/foto a cada passo que funciona.

**Divisão sugerida**
- **Emerson** — conduz os comandos no notebook e a ordem do roteiro.
- **Alessandro** — cuida do hardware (Pi, cabo, adaptador OBD-II no carro).

---

## Guia rápido: o que rodar, onde e quando

Tabela de relance. Os detalhes de cada passo estão nas seções abaixo.

| O que rodar               | Em qual máquina    | Quando                              |
|---------------------------|--------------------|-------------------------------------|
| `gerar_pki.sh`            | qualquer uma       | a qualquer momento (independe)      |
| `coletar_obd.py`          | a que tem o OBD-II | uma vez (talvez já feito)           |
| `coletor_recursos.py`     | **Raspberry Pi**   | Etapa 1 — abrir **1º**              |
| `rest_server.py`          | **Raspberry Pi**   | Etapa 1 — abrir **2º**              |
| `cliente_carga.py`        | **notebook**       | Etapa 1 — rodar **3º**              |
| `compilar_proto.sh`       | Pi e notebook      | Etapa 2 — só **após** a Etapa 1     |
| `grpc_server.py`          | **Raspberry Pi**   | Etapa 2                             |
| `cliente_grpc.py`         | **notebook**       | Etapa 2                             |

**Duas regras que não podem quebrar:**
1. **A ordem importa** — nunca rode a Etapa 2 antes da Etapa 1 passar.
2. **A máquina importa** — servidor e coletor sempre no **Pi** (é o hardware que
   queremos medir); cliente sempre no **notebook**. Trocar isso invalida os números.

> Antes de tudo: o repositório precisa estar **baixado nas duas máquinas**
> (Pi e notebook), senão os scripts não têm o que rodar.

---

## 0. Preparar o ambiente (~20-40 min)
Faça isto ANTES de qualquer teste. O `pip install` é o passo mais lento —
deixe rodando enquanto configura o cabo.

- [ ] Pi em **modo console** (não no desktop gráfico).
- [ ] **Repositório baixado nas duas máquinas** (ver "Como baixar o repositório" abaixo).
- [ ] Cabo Ethernet ligando Pi ↔ notebook.
- [ ] IPs fixos: Pi `192.168.50.1`, notebook `192.168.50.2` (comandos no README).
- [ ] `ping 192.168.50.1` do notebook responde. **← só siga se isto funcionar.**
- [ ] `pip install -r requirements.txt` nas duas máquinas.

### Como baixar o repositório

**No Raspberry Pi** (precisa de internet — o WiFi dele serve; o cabo é só para o experimento).
Quatro comandos:

    wget https://github.com/emerdesenv/rest-vs-grpc-veicular/archive/refs/heads/main.zip
    unzip main.zip
    cd rest-vs-grpc-veicular-main
    ls

O `ls` deve listar as pastas (`servers`, `client`, `data`...). É de dentro dessa
pasta (com sufixo `-main`, normal do GitHub) que todos os comandos são rodados.

- Se disser que `unzip` não existe:  `sudo apt install unzip -y` e repita o `unzip`.
- Se o `wget` der erro 404:  troque `main` por `master` no link.

**No notebook** (tem navegador): abrir o repositório → botão verde **Code → Download ZIP** → descompactar com dois cliques.

**Plano B (sem internet no Pi):** baixar o ZIP no notebook, passar por **pendrive**
para o Pi e descompactar lá. Zero git, zero comando de rede.

> Baixar o ZIP dá uma cópia "solta" (desconectada do GitHub), o que é perfeito
> para só **executar** hoje. Publicar resultados de volta no repositório é outra
> etapa, com git, para depois dos testes.


## 1. Etapa 1 — validar a encanação (REST) (~30-60 min)
Três terminais, na ordem do README: coletor (Pi) → servidor (Pi) → cliente (notebook).

- [ ] Cliente imprime P50/P95/P99 e gera `latencias_etapa1.csv`.
- [ ] Coletor (Ctrl+C) gera `recursos_pi.csv` com CPU/RAM.
- [ ] **📸 Print dos três terminais + foto do setup montado.**

> Se a Etapa 1 fechar, a parte mais difícil está vencida. O resto é bônus.

## 2. Coletar o CSV real (OBD-II) — Parte A do tutorial
Independe do resto; dá pra fazer em paralelo se tiver o carro por perto.

- [ ] `pip install obd`, rodar `coletar_obd.py`, gerar `telemetria_real.csv`.
- [ ] **📸 Print da telemetria aparecendo na tela** (evidência forte para o artigo).

## 3. Gerar a PKI (mTLS) — Parte B do tutorial
Não precisa de carro nem de rede montada; dá pra fazer a qualquer momento.

- [ ] Conferir o IP no topo do `gerar_pki.sh`, rodar, ver "OK" nas duas linhas.
- [ ] Guardar a pasta `pki/` (chaves `.key` são segredo, não vão pro GitHub).

## 4. (Bônus) Etapa 2 — gRPC — só se a Etapa 1 passou
- [ ] `pip install -r requirements-etapa2.txt` (no Pi pode demorar — ver aviso no arquivo).
- [ ] `bash proto/compilar_proto.sh` (gera os módulos nas pastas certas).
- [ ] Rodar de novo o coletor de recursos no Pi, **com nome de arquivo diferente**
      pra não sobrescrever o da Etapa 1:
      `nice -n 10 python3 metrics/coletor_recursos.py recursos_pi_grpc.csv`
- [ ] Rodar `grpc_server.py` (Pi) e `cliente_grpc.py` (notebook).
- [ ] Se sair um P50/P95/P99: **ambos os protocolos validados no hardware.** 🎉

> Vale o esforço extra do coletor aqui: sem isso, vocês saem hoje com CPU/RAM
> só do REST, e a comparação de recursos entre os dois protocolos (um dos
> pontos centrais do artigo) fica sem dado de um dos dois lados.

## 5. Subir no GitHub
- [ ] `.gitignore` PRIMEIRO (garante que nenhuma chave suba).
- [ ] Restante do repositório (código, tutoriais, README, CSV de exemplo).
- [ ] Conferir que a pasta `pki/` e os `.key` **não** aparecem no repositório.

## 6. Evidências para a apresentação de segunda
Junte num só lugar:
- [ ] `latencias_etapa1.csv` e `recursos_pi.csv` (ou `recursos_pi_rest.csv`) —
      números reais do Pi na Etapa 1.
- [ ] `telemetria_real.csv` (prova da coleta OBD real).
- [ ] Pasta `pki/` gerada com os dois "OK" (print da tela do `gerar_pki.sh`) —
      mostra que a segurança já está scriptada, mesmo sem estar ligada ainda.
- [ ] Fotos/prints de cada passo que funcionou.
- [ ] (Se fez a Etapa 2) `latencias_grpc_etapa2.csv` e `recursos_pi_grpc.csv`.

> Nenhum desses itens depende de ter rodado ataque L7 (JSON Bomb) hoje — isso é
> Etapa 5 do roadmap, planejada e descrita no artigo, não prometida como
> resultado já executado nesta fase.

> À noite, mande os CSVs de saída que eu transformo em gráficos apresentáveis
> (latência por percentil, CPU/RAM no tempo) para o slide de viabilidade.

---

### Três regras de ouro
1. **Chave privada nunca sai da máquina nem vai pro GitHub.**
2. **Artigo = realidade:** anotem toda versão/hardware que divergir do texto.
3. **Print a cada sucesso:** é evidência e é o seu "ponto de retorno" se algo quebrar.
