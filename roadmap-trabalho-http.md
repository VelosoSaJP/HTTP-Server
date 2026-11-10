# Roadmap — Trabalho HTTP (Redes ICSR30)

09/11/2026

## O que muda em relação ao Trabalho 2

O Trabalho 3 é o servidor do Trabalho 2 com o protocolo próprio trocado por HTTP. O reuso é obrigatório e vai ser cobrado.

| | O que é |
| --- | --- |
| Fica quase igual | Criação do socket (`AF_INET` + `SOCK_STREAM`), `SO_REUSEADDR`, `bind`/`listen`, loop do `accept` com uma thread `daemon` por conexão, sanitização de caminho, verificação de existência, leitura do arquivo em blocos |
| Muda | O framing: o cabeçalho binário de 13 bytes dá lugar ao formato de texto do HTTP. A mensagem de erro padronizada vira código de status (404 etc.) com uma página HTML no corpo |
| Sai | `client.py` (o cliente agora é o navegador), chat, broadcast, lista de clientes com lock, SHA-256 |

### A mudança no framing

| | Metadados | Separação | Dados |
| --- | --- | --- | --- |
| Trabalho 2 | Cabeçalho fixo de 13 bytes + nome | Tamanhos lidos do cabeçalho | `tam_dados` bytes brutos |
| Trabalho 3 (HTTP) | Linha de requisição/status + cabeçalhos em texto, cada linha terminada em `\r\n` | Linha vazia: `\r\n\r\n` | `Content-Length` bytes de corpo |

O HTTP é híbrido: usa delimitador nos cabeçalhos e tamanho no corpo. No Trabalho 2 o delimitador foi descartado porque o conteúdo poderia contê-lo. Na defesa, saiba explicar por que aqui não é problema: o delimitador só é procurado nos cabeçalhos, que são texto, e nunca dentro do corpo.

## Fases 0 a 2: preparação e primeiro contato com o HTTP

### Fase 0 — Ponto de partida

- [ ] Começar a partir do código do Trabalho 2, e não de arquivos novos. O histórico mostra a evolução, comprova o reuso e serve de evidência de autoria.
- [ ] Montar a pasta raiz do site (pode ser a própria `arquivos/`) com `index.html`, uma página de 404, uma `.jpg`, uma `.png` e uma página que use `<img>` para as duas, para o navegador pedir vários recursos de uma vez.
- [ ] Deixar à mão `curl -v` e `nc`: eles são os clientes de teste no lugar do `client.py`.

### Fase 1 — Escutar o navegador

- [ ] Fazer a thread só imprimir o `repr` dos bytes recebidos e fechar a conexão. Abrir `http://127.0.0.1:8080/`.
- [ ] Observar: os `\r\n` e a linha vazia no fim, o pedido automático de `/favicon.ico` e as conexões que o Chrome abre e não envia nada (pré-conexões especulativas). O código vai precisar lidar com elas.
- Porta > 1024. Com `127.0.0.1` só a própria máquina conecta; para testar pelo celular, como sugere o `[IP_do_Servidor]` da especificação, usar `0.0.0.0`.

### Fase 2 — Primeira resposta, escrita à mão

- [ ] Responder com uma string fixa: linha de status, `Content-Type`, `Content-Length`, `Connection: close`, linha em branco e um HTML pequeno.
- [ ] Experimento 1: remover o `Content-Length`, depois colocar um valor menor e um maior que o certo, e ver como o navegador reage.
- [ ] Experimento 2: colocar "você" no corpo e comparar o `len` da string com o `len` dos bytes. É o "tamanho exato em bytes" que aparece na aba Network.

## Fase 3 — Projeto no papel (antes de codar)

Decidir e escrever a justificativa de cada item. Isso vira o README do zip e o roteiro da defesa oral, como no Trabalho 2.

- [ ] **Leitura da requisição:** `recv` em loop, acumulando até encontrar `\r\n\r\n`. Definir um limite de tamanho para os cabeçalhos e um timeout para quem conecta e não manda nada. O que responder se o limite estourar?
- [ ] **Parsing:** separar a linha de requisição em método, caminho e versão. Quando é 400 (malformada)? E se o método não for GET (405 ou 501)? Algum cabeçalho do navegador é necessário, ou só a primeira linha?
- [ ] **Tratamento do caminho:** remover a query string (`/foto.png?v=2`), mapear `/` para `index.html` e lidar com percent-encoding (`%20` em nomes com espaço). Decodificar antes ou depois de sanitizar? Pensar no que acontece com `%2e%2e`.
- [ ] **Montagem da resposta:** quais cabeçalhos vão (o exemplo do professor tem `Date`, `Server`, `Content-Type`, `Content-Length`, `Connection`) e uma tabela própria de extensão para MIME, com um tipo padrão para extensões desconhecidas. É essa tabela que aparece quando perguntarem do `Content-Type` dinâmico.
- [ ] **Texto vs binário:** o professor vai pedir "a diferença no código". Onde existe texto de fato na resposta (o cabeçalho) e onde só existem bytes (o corpo)? O que quebraria numa imagem aberta em modo texto? Decidir entre um caminho único para todos os tipos ou caminhos separados, e saber justificar.
- [ ] **Erros:** quais códigos implementar e se cada um leva uma página HTML. Decisão herdada: no Trabalho 2, "não existe" e "fora da pasta" viraram um erro só. Manter (404 para os dois) ou usar 403 no path traversal, mais visível no vídeo?
- [ ] **Conexão:** `Connection: close` (uma requisição por conexão) ou keep-alive. O primeiro é bem mais simples; o segundo fica como extra opcional.

## Fases 4 a 7: implementação

### Fase 4 — Leitura e parsing

- [ ] Implementar a leitura até o delimitador e o parsing da linha de requisição.
- [ ] Testar com `curl -v` e com requisições malformadas digitadas no `nc`. Nenhuma requisição ruim pode derrubar o servidor, só a thread daquela conexão.

### Fase 5 — Servir arquivos

- [ ] Reaproveitar a sanitização do Trabalho 2, adaptando para a barra inicial e o `index.html`.
- [ ] Verificar se é um arquivo regular e pegar o tamanho em bytes no sistema de arquivos para o `Content-Length`.
- [ ] Montar o cabeçalho com o `Content-Type` da tabela de MIME, enviá-lo e depois enviar o arquivo em blocos (o mesmo loop do Trabalho 2, agora sem o SHA).

### Fase 6 — Erros

- [ ] Página de 404, também com o `Content-Length` correto do corpo de erro.
- [ ] Os outros códigos decididos na Fase 3.
- [ ] Definir o que acontece com o `favicon.ico`: servir um ícone ou responder 404 são opções válidas.

### Fase 7 — Concorrência visível

- [ ] Log com o nome da thread em cada requisição, para mostrar várias rodando ao mesmo tempo.
- [ ] Provar que "uma não bloqueia a outra": imagem grande + throttling de rede no DevTools de uma aba; enquanto ela carrega devagar, a outra aba carrega na hora.
- Evitar `sleep` artificial no código final.

## Fases 8 e 9: testes e entrega

### Fase 8 — Testes (os itens do vídeo)

| Item do vídeo | Pontos | Como testar |
| --- | --- | --- |
| Multithreading e concorrência | 2,00 | Duas abas ao mesmo tempo, uma com throttling; log com o nome das threads |
| Mídia e tratamento binário | 2,00 | Página com HTML, JPEG e PNG renderizando |
| Cabeçalhos HTTP | 2,00 | Aba Network: status, `Content-Type` por extensão, `Content-Length` igual ao tamanho do arquivo |
| Erro 404 | 2,00 | Arquivo inexistente mostrando a página de erro do servidor |
| Segurança e robustez | 2,00 | Path traversal bloqueado; requisição malformada não derruba o servidor |

**Pegadinha do traversal:** o navegador normaliza `../` (e também `%2e%2e`) antes de enviar. Digitando `/../../etc/passwd` na barra, o pedido chega como `/etc/passwd` e nada foi testado. Para o ataque chegar de verdade, usar `curl --path-as-is` ou `nc`, e testar também `//etc/passwd` e variações codificadas.

- [ ] Rodar todos os testes da tabela.
- [ ] Rodar os testes de traversal fora do navegador.

### Fase 9 — Entrega

- [ ] Versão do código **sem comentários** para gravar o vídeo.
- [ ] Zip com o código comentado e um README com as justificativas da Fase 3.
- [ ] Roteiro de no máximo 5 minutos: parte 1 com os 5 itens da tabela, parte 2 com as 6 perguntas em ordem (sockets, multithreading, tratamento binário, cabeçalhos, 404, path traversal). Cronometrar antes de gravar.
- [ ] Link do YouTube nos comentários particulares do Classroom e zip na atividade.
