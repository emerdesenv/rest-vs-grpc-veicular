# Tutorial: gerar o CSV de telemetria e a PKI do mTLS

Guia passo a passo, sem pressupor experiência com código. São duas tarefas
independentes: a **Parte A** gera o CSV de telemetria real (OBD-II); a
**Parte B** gera os certificados do mTLS. Pode fazer uma sem a outra.

> Regra de ouro que vale para as duas partes: **chave privada (`.key`) nunca
> sai da máquina dela e nunca vai para o GitHub.**

---

## PARTE A — Gerar o CSV de telemetria (OBD-II)

### O que você vai precisar
- O adaptador OBD-II ligado no carro, com a **chave do veículo ligada**
  (não precisa estar em movimento — parado na garagem coleta igual).
- O adaptador reconhecido no Linux (você já conseguiu isso antes).

### Passo 1 — Instalar a biblioteca (uma vez só)
No terminal:

    pip install obd

### Passo 2 — Descobrir a porta do adaptador (se não conectar sozinho)
- Adaptador **USB**: geralmente `/dev/ttyUSB0`.
- Adaptador **Bluetooth**: geralmente `/dev/rfcomm0` (depois de parear).

Para ver o que apareceu ao plugar:

    ls /dev/ttyUSB*      # para USB
    ls /dev/rfcomm*      # para Bluetooth

### Passo 3 — Coletar
Com o carro ligado, na pasta `data/`:

    python3 coletar_obd.py

Se ele reclamar que não conectou, informe a porta na mão:

    python3 coletar_obd.py /dev/ttyUSB0

### O que deve acontecer (sucesso)
A tela começa a imprimir uma linha por segundo, tipo:

    velocidade=0 | rpm=780 | temp_motor=88 | carga_motor=21 | ...

Deixe rodar o tempo que quiser (1–2 minutos já dá bastante dado). Aperte
**Ctrl+C** para parar. Vai gerar o arquivo **`telemetria_real.csv`** na pasta.
Pronto — é esse arquivo que substitui o `exemplo_telemetria.csv`.

### Erros comuns
- *"não conectou"* → chave do carro ligada? porta certa? Tente `sudo python3 coletar_obd.py /dev/ttyUSB0`.
- *"permission denied" na porta* → rode uma vez: `sudo usermod -aG dialout $USER` e reinicie a sessão.
- *Colunas vindo vazias* → nem todo carro expõe todos os PIDs; tudo bem, as que
  vierem já servem. Anote quais funcionaram (isso vira nota no artigo).

### Observação (não trava nada agora)
O OBD-II **não** fornece GPS. As colunas de latitude/longitude entram depois,
de um módulo GPS ou de um log do celular. Para a fase de proposta, a telemetria
OBD real já é a evidência que importa.

---

## PARTE B — Gerar a PKI do mTLS (certificados)

Isso cria a "identidade" digital de cada lado: uma **CA** (autoridade que
assina), um certificado para o **servidor** (o Pi) e um para o **cliente** (o
notebook). No mTLS, os dois se provam mutuamente usando esses certificados.

### Passo 1 — Conferir o IP do servidor
Abra o arquivo `gerar_pki.sh` e veja a linha do topo:

    IP_SERVIDOR="192.168.50.1"

Ela **precisa** ser o IP do Raspberry Pi (o servidor). Se vocês usaram outro IP
no cabo, troque aqui. (Esse IP é gravado dentro do certificado; se estiver
errado, o TLS recusa a conexão depois.)

### Passo 2 — Rodar
Na pasta `pki-scripts/`:

    bash gerar_pki.sh

### O que deve acontecer (sucesso)
Ele imprime os três passos e termina com:

    >> Conferencia (deve dizer 'OK' nas duas linhas):
    server.crt: OK
    client.crt: OK

E cria a pasta `pki/` com seis arquivos. O que é cada um:

| Arquivo      | Vai para              | Papel                                    |
|--------------|-----------------------|------------------------------------------|
| `ca.crt`     | **as duas** máquinas  | a autoridade que valida os certificados  |
| `server.key` | **só no Pi**          | chave privada do servidor (segredo)      |
| `server.crt` | Pi                    | certificado do servidor                  |
| `client.key` | **só no notebook**    | chave privada do cliente (segredo)       |
| `client.crt` | notebook              | certificado do cliente                   |
| `ca.key`     | guardar em segurança  | chave da CA (assina novos certificados)  |

### Regras de segurança (importantes)
- Os arquivos `.key` são **segredo**. Nunca vão para o GitHub — o `.gitignore`
  do repositório já bloqueia isso, mas confira antes de subir.
- `ca.key` é o mais sensível: quem tem ele pode forjar certificados válidos.
  Guarde num lugar seguro, fora do repositório.
- Se precisar regerar tudo, é só apagar a pasta `pki/` e rodar de novo.

---

## Depois de fazer as duas partes
- Aponte os clientes para o CSV real passando o caminho como segundo
  argumento (não precisa editar o código):

      python3 cliente_carga.py 192.168.50.1 ../data/telemetria_real.csv
      python3 cliente_grpc.py 192.168.50.1 ../data/telemetria_real.csv

  Sem esse argumento, os dois continuam usando `data/exemplo_telemetria.csv`.
- Guarde a pasta `pki/` nas máquinas certas; ela será usada quando o
  experimento chegar na Etapa 3 (segurança).
