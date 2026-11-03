# TCP-Protocol-Aplication
# Trabalho 2 de Redes (ICSR30) - Cliente/Servidor TCP

Aplicação cliente-servidor sobre TCP com servidor multithread, transferência de arquivos com verificação de integridade (SHA-256) e chat.

## Estrutura

- `server.py`: servidor TCP multithread
- `client.py`: cliente com menu interativo
- `tcp.py`: definição do protocolo (tipos de mensagem, cabeçalho e funções de envio/recepção)
- `arquivos/`: único diretório servido pelo servidor
- `download/`: onde o cliente salva os arquivos baixados

## Como executar

    python3 server.py
    python3 client.py

Para gerar um arquivo de teste maior que 10 MB (não versionado):

    dd if=/dev/urandom of=arquivos/grande.bin bs=1M count=20

## Protocolo

O TCP entrega um fluxo de bytes e não preserva os limites entre os envios. Por isso, toda mensagem segue o formato:

| Parte     | Tamanho                  | Conteúdo                                     |
|-----------|--------------------------|----------------------------------------------|
| Cabeçalho | 13 bytes (fixo)          | tipo, tam_nome, tam_dados                    |
| Nome      | tam_nome bytes           | nome do arquivo ou do remetente              |
| Dados     | tam_dados bytes          | bytes do arquivo, texto do chat, hash, erro  |

### Cabeçalho

| Campo     | Tamanho | Formato struct |
|-----------|---------|----------------|
| tipo      | 1 byte  | B              |
| tam_nome  | 4 bytes | I              |
| tam_dados | 8 bytes | Q              |

Formato `!BIQ`, em ordem de rede (big-endian) e sem padding.

### Tipos de mensagem

| tipo | Mensagem          | Quem envia | Nome                       | Dados                      |
|------|-------------------|------------|----------------------------|----------------------------|
| 1    | Pedido de arquivo | Cliente    | nome do arquivo pedido     | vazio                      |
| 2    | Arquivo           | Servidor   | nome do arquivo            | todos os bytes do arquivo  |
| 3    | Hash              | Servidor   | nome do arquivo            | SHA-256 em hexadecimal     |
| 4    | Erro              | Servidor   | nome do arquivo que falhou | descrição do erro          |
| 5    | Chat do cliente   | Cliente    | vazio                      | texto da mensagem          |
| 6    | Chat do servidor  | Servidor   | remetente                  | texto da mensagem          |
| 7    | Sair              | Cliente    | vazio                      | vazio                      |

### Sequências

- Download com sucesso: 1 → 2 → 3
- Download com falha: 1 → 4
- Chat do servidor: 6, a qualquer momento fora de uma mensagem 2
- Chat do cliente: 5, exibido apenas no console do servidor
- Encerramento: 7, e o cliente fecha a conexão

## Decisões de projeto

**Framing por tamanho.** O receptor sempre lê primeiro os 13 bytes do cabeçalho e, com eles, sabe exatamente quantos bytes de nome e de dados vêm em seguida. Não foi usado delimitador porque o conteúdo poderia conter o próprio delimitador e o receptor teria que procurá-lo byte a byte.

**tam_dados com 8 bytes.** O arquivo inteiro vai em uma única mensagem, então tam_dados é o tamanho do arquivo. Com 4 bytes o limite seria de cerca de 4 GB; com 8 bytes não há limite prático, ao custo de 4 bytes a mais por mensagem.

**Arquivo em uma única mensagem.** Simplifica o protocolo e o cliente, que recebe o arquivo num único loop. Em troca, enquanto um arquivo está sendo enviado nenhuma outra mensagem pode entrar na conexão, então um chat do servidor para aquele cliente espera o fim da transferência.

**Hash depois do arquivo.** O SHA-256 é calculado durante o envio, lendo o arquivo em blocos de 8 KB, sem carregá-lo inteiro na memória. Como só fica pronto depois do último bloco, vai numa mensagem separada (tipo 3). O cliente calcula o hash da mesma forma enquanto grava e compara os dois no final. O formato hexadecimal facilita a exibição e a comparação.

**Erro único.** Arquivo inexistente e tentativa de acesso fora de `arquivos/` geram a mesma mensagem de erro, para que não seja possível descobrir quais arquivos existem fora do diretório comparando as respostas.

**Nome do arquivo no cliente.** O cliente salva o download com o nome que ele mesmo pediu, e não com o nome recebido do servidor, evitando gravar fora de `download/`.

**Limite do nome.** Nomes acima de TAMANHO_MAX_NOME bytes são rejeitados, para que um tam_nome enorme não faça o servidor tentar ler e alocar gigabytes.

**SO_REUSEADDR.** Permite reiniciar o servidor logo após derrubá-lo, sem esperar as conexões antigas saírem do estado TIME_WAIT.
