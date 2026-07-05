# Aviso — isto NÃO é evidência oficial

Os 4 arquivos desta pasta (`ataque_rest_jsonbomb.csv`,
`ataque_rest_malformado.csv`, `ataque_grpc_jsonbomb.csv`,
`ataque_grpc_malformado.csv`) são resíduos de trilha de debug, não
evidência limpa de nenhum cenário do artigo. Motivo:

`client/atacante_l7.py` grava sempre no mesmo nome de arquivo quando
`--seguranca none --rede direto` (o padrão). Esses nomes foram
reaproveitados várias vezes ao longo do dia para propósitos diferentes:

- Testes locais no notebook (Windows, Python 3.11, `127.0.0.1`) durante o
  desenvolvimento do script.
- A bisseção de profundidade do JSON Bomb (testando profundidade 100, 500,
  900, 950, 980, 1000, 2000, 5000, 10000, 20000, 50000...) contra o Pi
  real, sem fixar `--seguranca`/`--rede`.

Cada execução nova sobrescreveu a anterior, então o conteúdo atual de
cada arquivo reflete só a **última** chamada com esses parâmetros
default naquele dia — não uma medição única e identificável.

O achado importante dessa investigação (o ponto de quebra por
profundidade de aninhamento, ~950-980 no notebook / ~5000-10000 no Pi)
já está registrado em `../README.md`, na seção da Etapa 5 — não depende
destes CSVs para ser reproduzido, só da profundidade usada em cada
chamada de `atacante_l7.py --profundidade N`.

Estes arquivos foram mantidos aqui (em vez de apagados) só como trilha
factual de que os testes de bisseção aconteceram, não como dado a citar
no artigo.
