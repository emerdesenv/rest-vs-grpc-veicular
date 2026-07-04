# Roteiro do dia de teste

Sequência única da sessão, na ordem. A ideia é fechar a **base** com folga e
avançar só até onde der sem atropelar. Print/foto a cada passo que funciona.

**Divisão sugerida**
- **Emerson** — conduz os comandos no notebook e a ordem do roteiro.
- **Alessandro** — cuida do hardware (Pi, cabo, adaptador OBD-II no carro).

---

## 0. Preparar o ambiente (~20-40 min)
Faça isto ANTES de qualquer teste. O `pip install` é o passo mais lento —
deixe rodando enquanto configura o cabo.

- [ ] Pi em **modo console** (não no desktop gráfico).
- [ ] Cabo Ethernet ligando Pi ↔ notebook.
- [ ] IPs fixos: Pi `192.168.50.1`, notebook `192.168.50.2` (comandos no README).
- [ ] `ping 192.168.50.1` do notebook responde. **← só siga se isto funcionar.**
- [ ] `pip install -r requirements.txt` nas duas máquinas.

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
- [ ] Rodar `grpc_server.py` (Pi) e `cliente_grpc.py` (notebook).
- [ ] Se sair um P50/P95/P99: **ambos os protocolos validados no hardware.** 🎉

## 5. Subir no GitHub
- [ ] `.gitignore` PRIMEIRO (garante que nenhuma chave suba).
- [ ] Restante do repositório (código, tutoriais, README, CSV de exemplo).
- [ ] Conferir que a pasta `pki/` e os `.key` **não** aparecem no repositório.

## 6. Evidências para a apresentação de segunda
Junte num só lugar:
- [ ] `latencias_etapa1.csv` e `recursos_pi.csv` (números reais do Pi).
- [ ] `telemetria_real.csv` (prova da coleta OBD real).
- [ ] Fotos/prints de cada passo que funcionou.
- [ ] (Se fez a Etapa 2) `latencias_grpc_etapa2.csv`.

> À noite, mande os CSVs de saída que eu transformo em gráficos apresentáveis
> (latência por percentil, CPU/RAM no tempo) para o slide de viabilidade.

---

### Três regras de ouro
1. **Chave privada nunca sai da máquina nem vai pro GitHub.**
2. **Artigo = realidade:** anotem toda versão/hardware que divergir do texto.
3. **Print a cada sucesso:** é evidência e é o seu "ponto de retorno" se algo quebrar.
