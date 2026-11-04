# Roadmap — Trabalho TCP (Redes ICSR30)

Oct 26, 2026 · @Joao

## O que muda em relação ao UDP

No UDP você tinha mensagens com fronteiras e precisava cuidar de perda e ordem. No TCP é o contrário: o TCP já garante entrega e ordem, mas entrega um **fluxo de bytes sem fronteiras**. Um `recv(4096)` pode trazer meia mensagem ou duas mensagens coladas. Quase todo o trabalho gira em torno disso e da concorrência.

Papel do Claude neste trabalho: apenas consultivo. Tira dúvidas, aponta próximos passos e revisa; o código é todo seu (no máximo trechos de pseudocódigo).

## Fases 0 a 2: base do servidor

### Fase 0 — Preparação

- [x] Confirmar a linguagem (provavelmente Python de novo).
- [x] Criar a pasta `arquivos/` e gerar um arquivo de teste com mais de 10 MB.

* Restrição importante: usar só o módulo `socket` puro e `threading`. Evitar `socketserver`, `asyncio` streams e similares, porque abstraem a conexão.

### Fase 1 — Hello World TCP

- [x] Fazer um servidor de eco e um cliente, com um cliente por vez.
- [x] Identificar no código o que garante que o socket é TCP (vai ser mostrado no vídeo).
- [x] Entender o ciclo `bind → listen → accept → recv/send → close` e a diferença entre o socket de escuta e o socket da conexão.
- [x] Testar o que `recv` retorna quando o outro lado fecha a conexão. Isso será usado para detectar desconexão.

### Fase 2 — Servidor multithread

- [x] Fazer o loop do `accept` criar uma thread por cliente, passando o socket da conexão.
- [x] Testar com dois clientes ao mesmo tempo (o `nc` ajuda a testar rápido).
- [x] Definir como guardar a lista de clientes conectados, necessária no broadcast. Essa lista é compartilhada entre threads, então precisa de lock.

## Fase 3 — Projeto do protocolo (no papel, antes de codar)

Esta é a fase mais importante. Escreva as justificativas enquanto decide: elas viram o README do zip e o roteiro da defesa oral.

- **Cabeçalho de tamanho fixo**: por exemplo, tipo da mensagem e tamanho do payload. Que tamanho de campo é preciso para o comprimento? Quatro bytes bastam para os arquivos que serão testados?
- **Tabela de tipos de mensagem**: comando Arquivo, comando Chat, Sair, metadados do arquivo, bloco de dados, fim do arquivo/hash, erro, chat do servidor.
- **Função "receber exatamente N bytes"**: a base de todo o framing. Chama `recv` em loop até completar N bytes ou detectar conexão fechada.
- **Quando enviar o SHA**: antes dos dados (o arquivo seria lido duas vezes) ou depois (calculado enquanto envia)? A especificação fala em hash "em tempo real", alimentado durante o envio. Qual opção combina com isso?
- **Como enviar os dados do arquivo**: em vários frames (cada bloco com seu cabeçalho) ou num bloco bruto de N bytes depois dos metadados? Isso afeta diretamente a Fase 6.

## Fases 4 a 7: comandos, concorrência e arquivos

### Fase 4 — Loop de comandos

- [x] No servidor, a thread de cada cliente fica num loop: lê o cabeçalho, despacha pelo tipo e trata.
- [x] No cliente, criar o menu (Sair, Arquivo, Chat). Começar só com Sair e Chat.

### Fase 5 — Concorrência no cliente

- [ ] Duas threads: a principal lê o teclado e uma thread separada lê o socket.

* **Ponto-chave**: se só a thread leitora lê o socket, como os dados do download chegam até quem salva o arquivo? Duas threads lendo o mesmo socket causam condição de corrida. Pense numa thread leitora que recebe tudo e despacha por tipo, inclusive os blocos do arquivo.
* Detalhe estético: o chat chegando bagunça o prompt do `input()`. Reimprimir o prompt resolve.

### Fase 6 — Broadcast do servidor

- [ ] Criar uma thread no servidor que lê o console e envia para todos os clientes da lista.

* **Ponto-chave**: o que acontece se o broadcast chegar no meio do envio de um arquivo para aquele cliente? Duas threads escrevendo no mesmo socket podem intercalar bytes no meio de um frame. Considere um lock de envio por conexão e se o framing permite intercalar chat entre os blocos.

### Fase 7 — Transferência de arquivos

- [ ] **Sanitização**: resolver o caminho canônico (absoluto, sem `..`, com symlinks resolvidos) e verificar se ele continua dentro da pasta raiz. Concatenar e procurar `..` na string não basta. Lembrar de caminhos absolutos (`/etc/passwd`), nome vazio e diretórios.
- [ ] **Existência**: verificar se o arquivo existe e responder com uma mensagem de erro padronizada caso não exista.
- [ ] **Envio**: ler em blocos de 4 ou 8 KB, atualizar o hash a cada bloco e enviar. Nunca ler o arquivo inteiro na memória.
- [ ] **No cliente**: gravar em disco bloco a bloco, calcular o hash local incrementalmente e comparar com o hash do servidor no final.

## Fases 8 e 9: testes e entrega

### Fase 8 — Testes (exatamente o que o vídeo pede)

- [ ] Dois clientes simultâneos e um broadcast chegando enquanto um deles espera digitação.
- [ ] Download maior que 10 MB com a verificação de SHA aprovada.
- [ ] Arquivo inexistente.
- [ ] Tentativas de path traversal com `../../etc/passwd`, `/etc/passwd` e `..`.
- [ ] Extra: chat durante um download.
- [ ] Extra: dois downloads ao mesmo tempo.
- [ ] Extra: cliente fechado à força (o servidor não pode cair e deve tirar o cliente da lista).

### Fase 9 — Entrega

- [ ] Versão do código **sem comentários** para gravar o vídeo.
- [ ] Zip com o código comentado e o README com as justificativas do protocolo.
- [ ] Roteiro do vídeo com no máximo 5 minutos: parte 1 é a demonstração, parte 2 responde as 6 perguntas em ordem. Cronometrar antes de gravar.
- [ ] Enviar o link do YouTube como comentário particular no Classroom.

Em aberto: confirmar a linguagem e o prazo de entrega para distribuir as fases no tempo.
