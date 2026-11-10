import socket
import threading
import os
import hashlib
import protocol

HOST = "127.0.0.1"
PORT = 8080


def enviar_arquivo(conexao, nome):
	pasta_arquivo = "files"
	caminho = os.path.join(pasta_arquivo, nome)

	if os.path.basename(nome) != nome or not os.path.isfile(caminho):
		protocol.enviar_mensagem(conexao, protocol.Tipo.ERRO, nome, "Arquivo não encontrado")
		return None

	tamanho = os.path.getsize(caminho)
	hash_sha = hashlib.sha256()

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


def atender_cliente(conexao, endereco):
	with conexao:
		print(f"Conectado: {endereco}")

		dados = conexao.recv(1024)

		print(f"{endereco} enviou {len(dados)} bytes:")
		print(repr(dados))


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:

	servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
	servidor.bind((HOST, PORT))
	
	servidor.listen()
	print(f"Server escutando em {HOST}:{PORT} e aguardando conexões...")

	while True:
		conexao, endereco = servidor.accept()

		thread = threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True)
		thread.start()
