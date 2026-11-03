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