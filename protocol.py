import struct
from enum import IntEnum


class Tipo(IntEnum):
	PEDIDO_ARQUIVO = 1
	ARQUIVO = 2
	HASH = 3
	ERRO = 4
	CHAT_CLIENTE = 5
	CHAT_SERVIDOR = 6
	SAIR = 7


FORMATO_CABECALHO = "!BIQ"

TAMANHO_CABECALHO = struct.calcsize(FORMATO_CABECALHO)
TAMANHO_BLOCO = 8192
TAMANHO_MAX_NOME = 255


def montar_cabecalho(tipo, tam_nome, tam_dados):
	return struct.pack(FORMATO_CABECALHO, tipo, tam_nome, tam_dados)


def ler_cabecalho(cabecalho):
	
	tipo, tam_nome, tam_dados = struct.unpack(FORMATO_CABECALHO, cabecalho)
	
	return Tipo(tipo), tam_nome, tam_dados


def receber_bytes(sock, n):
	buffer = b""

	while len(buffer) < n:
		pedaco = sock.recv(n - len(buffer))

		if not pedaco:
			raise ConnectionError("Conexão fechada")

		buffer += pedaco

	return buffer


def enviar_inicio(sock, tipo, nome, tam_dados):
	nome_bytes = nome.encode("utf-8")
	cabecalho = montar_cabecalho(tipo, len(nome_bytes), tam_dados)

	sock.sendall(cabecalho + nome_bytes)


def enviar_mensagem(sock, tipo, nome, dados):
	dados_bytes = dados.encode("utf-8")

	enviar_inicio(sock, tipo, nome, len(dados_bytes))
	sock.sendall(dados_bytes)


def receber_inicio(sock):
	cabecalho = receber_bytes(sock, TAMANHO_CABECALHO)
	tipo, tam_nome, tam_dados = ler_cabecalho(cabecalho)

	if tam_nome > TAMANHO_MAX_NOME:
		raise ValueError("Nome grande demais")

	nome = receber_bytes(sock, tam_nome).decode("utf-8")

	return tipo, nome, tam_dados
