# Servidor Web HTTP Multithread

Trabalho 3 da disciplina de Redes de Computadores (ICSR30), do Prof. Mauro Fonseca (UTFPR, DAINF).

Servidor HTTP simplificado sobre TCP, construído a partir do servidor multithread do Trabalho 2. O cliente é o navegador: o servidor interpreta a requisição HTTP, responde com o cabeçalho correto e envia o arquivo pedido, tratando várias conexões ao mesmo tempo, arquivos binários e situações de erro.

## Estrutura

- `server.py`: socket TCP, loop do `accept`, uma thread por conexão e envio dos arquivos
- `protocol.py`: o protocolo HTTP (leitura da requisição, parsing, montagem do cabeçalho e tabela de tipos MIME)
- `files/`: pasta raiz do site, único diretório servido pelo servidor

## Como executar

O servidor deve ser executado de dentro da pasta do projeto, pois `files/` é um caminho relativo ao diretório atual.

    python3 server.py

Depois, abrir no navegador `http://127.0.0.1:8080/`.

## Protocolo

O servidor fala HTTP/1.1 com uma requisição por conexão. Tanto a requisição quanto a resposta seguem a mesma estrutura:

| Parte | Formato |
|-------|---------|
| Primeira linha | linha de requisição (`GET /index.html HTTP/1.1`) ou de status (`HTTP/1.1 200 OK`), terminada em `\r\n` |
| Cabeçalhos | um `Nome: valor` por linha, cada uma terminada em `\r\n` |
| Linha em branco | `\r\n`, que junto com o fim da última linha forma o `\r\n\r\n` |
| Corpo | exatamente `Content-Length` bytes |

### Resposta

    HTTP/1.1 200 OK
    Date: Tue, 10 Nov 2026 20:00:00 GMT
    Server: ServidorRedes/1.0
    Content-Type: text/html; charset=utf-8
    Content-Length: 237
    Connection: close

    (237 bytes do arquivo)

### Códigos de status

| Código | Quando | Corpo |
|--------|--------|-------|
| 200 OK | arquivo encontrado | o arquivo |
| 400 Bad Request | linha de requisição malformada ou cabeçalho maior que o limite | HTML gerado no código |
| 403 Forbidden | caminho com diretório (tentativa de sair da pasta raiz) | HTML gerado no código |
| 404 Not Found | arquivo inexistente ou que não é um arquivo regular | `files/404.html` |
| 501 Not Implemented | método diferente de GET | HTML gerado no código |

### Tipos MIME

| Extensão | Content-Type |
|----------|--------------|
| `.html` | `text/html; charset=utf-8` |
| `.txt` | `text/plain; charset=utf-8` |
| `.jpg`, `.jpeg` | `image/jpeg` |
| `.png` | `image/png` |
| `.ico` | `image/x-icon` |
| outras | `application/octet-stream` |

### Fluxo de uma requisição

```
Navegador                          Servidor (accept)           Thread da conexão
   |--- connect (handshake TCP) ------>|                               |
   |                                   |-- cria thread com o socket -->|
   |                                   |   da conexão                  |
   |--- GET /index.html HTTP/1.1 ... \r\n\r\n ------------------------>|  lê até o \r\n\r\n,
   |                                                                   |  valida e procura
   |                                                                   |  o arquivo
   |<------------------------------- HTTP/1.1 200 OK ... \r\n\r\n -----|
   |<------------------------------- N bytes, em blocos de 8 KB -------|
   |<------------------------------- fecha a conexão ------------------|
```

Ao receber o HTML, o navegador pede os outros recursos da página (imagens e o `favicon.ico`), cada um na sua própria conexão.

## Decisões de projeto

### Leitura da requisição

**Leitura até o delimitador.** O TCP não preserva os limites das mensagens, então uma requisição pode chegar em vários `recv`. A thread acumula os bytes recebidos num buffer até encontrar `\r\n\r\n`, o fim dos cabeçalhos. O corpo da requisição não é lido, porque o servidor só aceita GET, que não tem corpo.

**Delimitador e tamanho juntos.** O HTTP usa delimitador nos cabeçalhos e tamanho no corpo. O problema de o conteúdo conter o próprio delimitador não aparece aqui: o `\r\n\r\n` só é procurado nos cabeçalhos, que são texto e não podem contê-lo antes do fim. O corpo, que pode conter qualquer byte, nunca é varrido em busca dele, pois seu fim é dado pelo `Content-Length`.

**Limite de 8 KB nos cabeçalhos.** Sem limite, um cliente poderia enviar bytes indefinidamente sem nunca mandar o `\r\n\r\n` e fazer o buffer crescer até esgotar a memória. Se o limite estourar, a resposta é 400. Um navegador comum envia menos de 1 KB.

**Timeout de 5 segundos.** O Chrome abre conexões especulativas que muitas vezes não enviam nada. Sem timeout, cada uma prenderia uma thread parada no `recv`. Quem não completa a requisição dentro do prazo tem a conexão fechada sem resposta. O mesmo vale para um cliente que fecha a conexão antes do `\r\n\r\n`.

### Parsing

**Só a linha de requisição importa.** Ela é dividida por espaços e precisa ter exatamente três partes: método, caminho e versão, com a versão começando por `HTTP/`. Qualquer outra forma gera 400. Os demais cabeçalhos são ignorados, porque nenhum deles é necessário para servir um arquivo.

**Decodificação em latin-1.** Os bytes do cabeçalho são convertidos para texto com latin-1, que associa cada byte a um caractere e nunca falha. Uma requisição com bytes inválidos é tratada como malformada, e não derruba a thread com um erro de decodificação.

**501 para outros métodos.** O servidor só implementa GET. O 405 indicaria que o método existe no servidor mas não vale para aquele recurso, e exigiria o cabeçalho `Allow`. O 501 descreve melhor um método que o servidor não implementa em lugar nenhum.

### Tratamento do caminho

**Normalização.** O caminho precisa começar com `/`. A query string é descartada (`/foto.png?v=2` vira `/foto.png`), a barra inicial é removida e o caminho vazio, que corresponde a `/`, é mapeado para `index.html`.

**Sanitização.** É a mesma verificação do Trabalho 2: `os.path.basename(nome) != nome`. Se remover o caminho altera o nome, o pedido continha alguma barra (`../`, `/etc/`, `//`) e é recusado com 403. O nome não é reescrito para o `basename`, porque assim `../index.html` acabaria servindo `files/index.html` e pareceria que o acesso fora da pasta funcionou. Em seguida, `os.path.isfile` confirma que o arquivo existe e não é um diretório, o que também barra `..` e gera 404. Como consequência, subpastas dentro de `files/` não são servidas, o que não é necessário neste trabalho.

**403 e 404 separados.** No Trabalho 2, nome com caminho e arquivo inexistente geravam o mesmo erro, para não revelar o que existe fora da pasta. Aqui eles são separados para deixar o bloqueio visível, e isso continua sem revelar nada: o 403 é decidido só pelo formato do nome, antes de qualquer acesso ao disco. Um pedido de `../../etc/passwd` recebe 403 exista o arquivo ou não.

**Percent-encoding não é decodificado.** Sequências como `%20` e `%2e` são mantidas como texto literal. Se o caminho fosse decodificado, isso teria que acontecer antes da sanitização: decodificando depois, `%2e%2e%2f` passaria pela verificação e só então viraria `../`. Sem decodificar, `%2e%2e%2fetc%2fpasswd` não contém barra, passa pela verificação e simplesmente não existe como arquivo, gerando 404. O custo é não servir arquivos com espaço ou acento no nome, e o site não tem nenhum.

**Navegador e path traversal.** O navegador normaliza `../` (e também `%2e%2e`) antes de enviar o pedido, então digitar `/../../etc/passwd` na barra de endereços envia `/etc/passwd`. Para que o ataque chegue ao servidor como foi escrito, os testes usam `curl --path-as-is` ou `nc`.

### Montagem da resposta

**Cabeçalhos.** A resposta leva a linha de status, `Date`, `Server`, `Content-Type`, `Content-Length` e `Connection: close`, seguidos da linha em branco. A data é gerada no formato do HTTP, sempre em GMT.

**Content-Type pela extensão.** A extensão do arquivo é procurada numa tabela própria (um dicionário). Uma extensão desconhecida recebe `application/octet-stream`, que faz o navegador baixar o arquivo em vez de tentar exibi-lo.

**charset=utf-8 nos tipos de texto.** As páginas não declaram a codificação com `<meta charset>`. Sem o charset no cabeçalho, o navegador pode adivinhar outra codificação e exibir "você" como "vocÃª".

**Content-Length em bytes.** Para arquivos, o valor vem de `os.path.getsize`, que já é o tamanho em bytes no disco. Para as páginas de erro geradas no código, vem do `len` depois do `.encode()`. O `len` de uma string conta caracteres, e um caractere acentuado ocupa 2 bytes em UTF-8.

### Texto e binário

**Um caminho só para todos os arquivos.** Todo arquivo é aberto em modo binário (`"rb"`) e enviado em blocos de 8 KB, exatamente como está no disco. O servidor nunca decodifica o conteúdo: para ele, HTML, JPEG e PNG são apenas bytes, e quem os interpreta é o navegador, guiado pelo `Content-Type`.

**Onde existe texto.** Texto de verdade só aparece no que o próprio servidor escreve: o cabeçalho da resposta e as páginas de erro geradas no código. Eles são montados como string e convertidos para bytes com `.encode()` antes do envio.

**Por que não modo texto.** Ler uma imagem em modo texto faria o Python decodificá-la como UTF-8, o que gera `UnicodeDecodeError` ou troca bytes inválidos por caracteres de substituição. No Windows, o modo texto ainda converte `\n` em `\r\n`. Nos dois casos os bytes enviados deixariam de ser os do arquivo, a imagem chegaria corrompida e o tamanho deixaria de bater com o `Content-Length`.

**Leitura em blocos.** O arquivo não é carregado inteiro na memória, então o consumo é o mesmo para uma página de 200 bytes ou uma imagem de 20 MB.

### Conexão

**Connection: close.** Cada conexão atende uma única requisição, e o servidor fecha o socket depois de enviar a resposta. Isso evita controlar o fim de uma requisição e o início da próxima no mesmo socket. O `Content-Length` continua sendo enviado, como exige a especificação, e permite ao navegador saber se recebeu o corpo inteiro.

**SO_REUSEADDR.** Permite reiniciar o servidor logo após derrubá-lo, sem esperar as conexões antigas saírem do estado TIME_WAIT.

## Concorrência

**Uma thread por conexão.** O loop principal só faz `accept` e entrega o socket da conexão para uma thread nova, que roda `atender_cliente`. O estado da conexão (o socket, o endereço e o buffer da requisição) fica nas variáveis locais dessa thread. Uma requisição malformada ou uma desconexão encerram apenas a thread daquela conexão.

**Sem estado compartilhado.** No Trabalho 2, a lista de clientes e o broadcast exigiam locks. Aqui as threads não compartilham nada além da pasta `files/`, que só é lida, então não há lock.

**Concorrência do navegador.** Para montar uma página, o navegador abre várias conexões em paralelo, uma para cada recurso. Cada uma é atendida por uma thread diferente, e uma transferência lenta não impede que as outras terminem.
