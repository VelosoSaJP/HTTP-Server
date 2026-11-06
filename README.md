# Transferência de Arquivos e Chat sobre TCP

Trabalho 2 da disciplina de Redes de Computadores (ICSR30), do Prof. Mauro Fonseca (UTFPR, DAINF).

Aplicação cliente-servidor sobre TCP com servidor multithread, transferência de arquivos com verificação de integridade (SHA-256) e chat.

## Estrutura

- `server.py`: servidor TCP multithread
- `client.py`: cliente com menu interativo
- `protocol.py`: definição do protocolo (tipos de mensagem, cabeçalho e funções de envio/recepção)
- `files/`: único diretório servido pelo servidor
- `downloads/`: onde o cliente salva os arquivos baixados

## Como executar

Requer Python 3.10 ou mais novo, por causa do `match/case`. Os dois programas devem ser executados de dentro da pasta do projeto, pois `files/` e `downloads/` são caminhos relativos ao diretório atual.

    python3 server.py
    python3 client.py

No console do servidor, qualquer linha digitada é enviada como chat para todos os clientes conectados.

Para gerar um arquivo de teste maior que 10 MB (não versionado):

    dd if=/dev/urandom of=files/grande.bin bs=1M count=20

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
- Chat do servidor: 6, a qualquer momento fora de um download (nunca entre o 2 e o 3)
- Chat do cliente: 5, exibido apenas no console do servidor
- Encerramento: 7, o servidor fecha a conexão e o cliente termina ao detectar o fechamento

### Fluxo de uma transferência

```
Cliente                            Servidor (accept)           Thread do cliente
   |--- connect (handshake TCP) ------>|                               |
   |                                   |-- cria thread com o socket -->|
   |                                   |   da conexão                  |
   |--- 1 PEDIDO_ARQUIVO "grande.bin" -------------------------------->|  valida o nome e
   |                                                                   |  a existência
   |<------------------------------------ 2 ARQUIVO (tam_dados = N) ---|
   |<------------------------------------ N bytes, em blocos de 8 KB --|  SHA-256 atualizado
   |   grava e calcula o SHA-256 local                                 |  a cada bloco
   |<------------------------------------ 3 HASH "sha256 em hex" ------|
   |   compara os dois hashes                                          |
   |                                ...                                |
   |--- 7 SAIR ------------------------------------------------------->|
   |<------------------------------------ fecha a conexão -------------|
```

Todas as mensagens trafegam pelo mesmo socket da conexão. Se o nome tiver caminho ou o arquivo não existir, a thread responde com 4 ERRO em vez do 2, e o cliente mostra a mensagem ao usuário. Um chat do servidor (6) pode chegar antes do 2 ou depois do 3, mas nunca no meio da transferência.

## Decisões de projeto

**Framing por tamanho.** O receptor sempre lê primeiro os 13 bytes do cabeçalho e, com eles, sabe exatamente quantos bytes de nome e de dados vêm em seguida. Não foi usado delimitador porque o conteúdo poderia conter o próprio delimitador e o receptor teria que procurá-lo byte a byte.

**tam_dados com 8 bytes.** O arquivo inteiro vai em uma única mensagem, então tam_dados é o tamanho do arquivo. Com 4 bytes o limite seria de cerca de 4 GB; com 8 bytes não há limite prático, ao custo de 4 bytes a mais por mensagem.

**Arquivo em uma única mensagem.** Simplifica o protocolo e o cliente, que recebe o arquivo num único loop. Em troca, enquanto um arquivo está sendo enviado nenhuma outra mensagem pode entrar na conexão, então um chat do servidor para aquele cliente espera o fim da transferência.

**Hash depois do arquivo.** O SHA-256 é calculado durante o envio, lendo o arquivo em blocos de 8 KB, sem carregá-lo inteiro na memória. Como só fica pronto depois do último bloco, vai numa mensagem separada (tipo 3). O cliente calcula o hash da mesma forma enquanto grava e compara os dois no final. O formato hexadecimal facilita a exibição e a comparação.

**Sanitização do nome.** O servidor só aceita um nome de arquivo puro, sem nenhum diretório. A verificação é `os.path.basename(nome) != nome`: se remover o caminho altera o nome, o pedido continha alguma barra (`../`, `/etc/`, `files/`) e é recusado. O nome não é reescrito para o `basename`, porque assim `../foto.png` acabaria servindo `files/foto.png` e pareceria que o acesso fora da pasta funcionou. Em seguida, `os.path.isfile` confirma que o arquivo existe e não é um diretório, o que também barra `..` e o nome vazio. Como consequência, subpastas dentro de `files/` não são servidas, o que não é necessário neste trabalho.

**Erro único.** Arquivo inexistente e nome com caminho geram a mesma mensagem de erro, para que não seja possível descobrir quais arquivos existem fora do diretório comparando as respostas.

**Nome do arquivo no cliente.** O cliente salva o download com o nome que ele mesmo pediu, e não com o nome recebido do servidor, evitando gravar fora de `downloads/`.

**Limite do nome.** Nomes acima de TAMANHO_MAX_NOME bytes são rejeitados, para que um tam_nome enorme não faça o servidor tentar ler e alocar gigabytes.

**SO_REUSEADDR.** Permite reiniciar o servidor logo após derrubá-lo, sem esperar as conexões antigas saírem do estado TIME_WAIT.

## Concorrência

### Servidor

**Uma thread por cliente.** O loop principal só faz `accept` e entrega o socket da conexão para uma thread nova, que roda `atender_cliente`. O estado de cada conexão (o socket, o endereço e o lock de envio) fica nas variáveis locais dessa thread. Um erro ou desconexão encerra apenas a thread daquele cliente.

**Lista de clientes com lock.** O dicionário `clientes` guarda cada conexão ativa e é usado pelo broadcast. Ele é compartilhado entre todas as threads, então toda inclusão e remoção acontece dentro de `lock_clientes`. A remoção fica num `finally`, para que o cliente saia da lista em qualquer forma de encerramento, inclusive quando o processo do cliente é morto.

**Lock de envio por conexão.** Duas threads podem escrever no mesmo socket: a do cliente, enviando um arquivo, e a do broadcast. Sem controle, os bytes de um chat poderiam cair no meio dos bytes do arquivo e quebrar o framing. Cada conexão tem um `lock_envio`, e cada mensagem é enviada inteira com ele seguro. No download, o lock é mantido do início do arquivo até o envio do hash. Isso implementa a decisão de enviar o arquivo em uma única mensagem.

**Broadcast fora do lock da lista.** A thread de broadcast lê uma linha do console, copia a lista de clientes dentro de `lock_clientes` e só depois envia, já fora dele. Se o envio acontecesse com a lista travada, um broadcast esperando o fim de um download bloquearia a entrada e a saída de todos os outros clientes. Um cliente que caia entre a cópia e o envio gera um `OSError`, que é ignorado.

**Dois locks diferentes.** `lock_clientes` protege a lista de quem está conectado; `lock_envio` protege a escrita em cada socket.

### Cliente

**Duas threads.** A thread principal lê o teclado e envia comandos. Uma segunda thread fica bloqueada em `recv` e trata tudo o que chega do servidor. Com isso, um chat do servidor aparece mesmo enquanto a thread principal está parada no `input()`.

**Uma única thread lê o socket.** Se as duas threads chamassem `recv`, cada uma poderia ficar com um pedaço do mesmo frame. Por isso a thread leitora recebe todas as mensagens, inclusive os bytes do arquivo, e decide o que fazer pelo tipo.

**Prompt reimpresso.** Quando um chat chega, a linha do `input()` é sobrescrita. A thread leitora reimprime o último prompt mostrado, guardado em `prompt_atual`.

**Menu bloqueado durante o download.** Depois de pedir um arquivo, a thread principal espera um `threading.Event` até a thread leitora receber o hash ou o erro. Isso evita que o menu seja impresso no meio da saída do download e que um segundo pedido troque o nome do arquivo que ainda está sendo gravado. A thread leitora também libera esse evento se a conexão cair, para que a thread principal não fique presa.

**Encerramento.** Ao escolher Sair, o cliente envia a mensagem 7 e espera a thread leitora terminar com `join`. O servidor fecha a conexão, o `recv` da thread leitora retorna vazio e ela termina. O socket só é fechado depois disso, para não ser fechado enquanto outra thread ainda está bloqueada nele.
