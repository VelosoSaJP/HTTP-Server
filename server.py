import socket
import threading
import os
import hashlib
import protocol

HOST = "127.0.0.1"
PORT = 65432

PASTA_ARQUIVOS = "files"

clientes = {}
lock_clientes = threading.Lock()


def enviar_arquivo(conexao, lock_envio, nome):
	caminho = os.path.join(PASTA_ARQUIVOS, os.path.basename(nome))

	if not os.path.isfile(caminho):
		with lock_envio:
			protocol.enviar_mensagem(conexao, protocol.Tipo.ERRO, nome, "Arquivo não encontrado")
		return None

	tamanho = os.path.getsize(caminho)
	hash_sha = hashlib.sha256()

	with lock_envio:
		protocol.enviar_inicio(conexao, protocol.Tipo.ARQUIVO, nome, tamanho)

		with open(caminho, "rb") as arquivo:
			while True:
				bloco = arquivo.read(protocol.TAMANHO_BLOCO)

				if not bloco:
					break

				hash_sha.update(bloco)
				conexao.sendall(bloco)

		protocol.enviar_mensagem(conexao, protocol.Tipo.HASH, nome, hash_sha.hexdigest())

	return hash_sha.hexdigest()


def broadcast():
	while True:
		texto = input()

		with lock_clientes:
			destinos = list(clientes.items())

		for conexao, lock_envio in destinos:
			try:
				with lock_envio:
					protocol.enviar_mensagem(conexao, protocol.Tipo.CHAT_SERVIDOR, "Servidor", texto)
			except OSError:
				pass

		print(f"Broadcast enviado para {len(destinos)} clientes")


def atender_cliente(conexao, endereco):
	lock_envio = threading.Lock()

	with conexao:
		with lock_clientes:
			clientes[conexao] = lock_envio
			print(f"Conectado: {endereco} ({len(clientes)} clientes)")

		try:
			while True:
				tipo, nome, tam_dados = protocol.receber_inicio(conexao)

				if tipo == protocol.Tipo.SAIR:
					print(f"{endereco} saiu")
					break

				elif tipo == protocol.Tipo.CHAT_CLIENTE:
					texto = protocol.receber_bytes(conexao, tam_dados).decode("utf-8")
					print(f"[{endereco}] {texto}")

				elif tipo == protocol.Tipo.PEDIDO_ARQUIVO:
					print(f"{endereco} pediu o arquivo '{nome}'")
					hash_enviado = enviar_arquivo(conexao, lock_envio, nome)

					if hash_enviado is None:
						print(f"'{nome}' recusado para {endereco}")
					else:
						print(f"'{nome}' enviado para {endereco} (SHA-256 {hash_enviado})")

				else:
					print(f"{endereco} mandou uma mensagem inesperada: {tipo.name}")
					break

		except (ConnectionError, ValueError) as erro:
			print(f"{endereco} desconectou: {erro}")

		finally:
			with lock_clientes:
				del clientes[conexao]
				print(f"{endereco} removido ({len(clientes)} clientes)")


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:

	servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #resolve o problema de Adress alreday in use, mata o TIME_WAIT
	servidor.bind((HOST, PORT))
	
	servidor.listen()
	print(f"Server escutando em {HOST}:{PORT} e aguardando conexões...")
	print("Digite uma mensagem para enviar a todos os clientes")

	threading.Thread(target=broadcast, daemon=True).start()

	while True:
		conexao, endereco = servidor.accept()

		thread = threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True)
		thread.start()
