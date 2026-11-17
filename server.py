import socket
import threading
import os
import time
import protocol

HOST = "127.0.0.1"
PORT = 8080


def registrar(endereco, mensagem):
	horario = time.strftime("%H:%M:%S")
	nome_thread = threading.current_thread().name

	print(f"{horario} [{nome_thread}] {endereco} {mensagem}")


def transmitir_arquivo(conexao, status, caminho):
	tamanho = os.path.getsize(caminho)

	conexao.sendall(protocol.montar_cabecalho(status, protocol.tipo_mime(caminho), tamanho))

	with open(caminho, "rb") as arquivo:
		while True:
			bloco = arquivo.read(protocol.TAMANHO_BLOCO)

			if not bloco:
				break

			conexao.sendall(bloco)


def enviar_arquivo(conexao, nome):
	pasta_arquivo = "files"
	caminho = os.path.join(pasta_arquivo, nome)

	if os.path.basename(nome) != nome:
		protocol.enviar_erro(conexao, 403)
		return 403

	if not os.path.isfile(caminho):
		pagina_404 = os.path.join(pasta_arquivo, "404.html")

		if os.path.isfile(pagina_404):
			transmitir_arquivo(conexao, 404, pagina_404)
		else:
			protocol.enviar_erro(conexao, 404)

		return 404

	transmitir_arquivo(conexao, 200, caminho)

	return 200


def atender_cliente(conexao, endereco):
	with conexao:
		conexao.settimeout(protocol.TIMEOUT)

		try:
			cabecalho = protocol.receber_requisicao(conexao)
			metodo, caminho, versao = protocol.interpretar_requisicao(cabecalho)

		except (ConnectionError, TimeoutError):
			registrar(endereco, "fechou sem enviar uma requisição")
			return

		except ValueError as erro:
			registrar(endereco, f"400: {erro}")
			protocol.enviar_erro(conexao, 400)
			return

		registrar(endereco, f"{metodo} {caminho} {versao}")

		nome = protocol.extrair_nome(caminho)

		try:
			status = enviar_arquivo(conexao, nome)
			registrar(endereco, f"{status} {protocol.FRASES_STATUS[status]}: {nome}")

		except (ConnectionError, TimeoutError):
			registrar(endereco, f"desconectou durante o envio de {nome}")


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:

	servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
	servidor.bind((HOST, PORT))
	
	servidor.listen()
	print(f"Server escutando em {HOST}:{PORT} e aguardando conexões...")

	numero_conexao = 0

	while True:
		conexao, endereco = servidor.accept()
		numero_conexao += 1

		thread = threading.Thread(target=atender_cliente, args=(conexao, endereco), name=f"Thread-{numero_conexao}", daemon=True)
		thread.start()
