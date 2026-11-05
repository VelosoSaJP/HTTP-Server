import socket
import threading
import os
import hashlib
import protocol

HOST = "127.0.0.1"
PORT = 65432

PASTA_DOWNLOADS = "downloads"

prompt_atual = ""
arquivo_pedido = ""
download_concluido = threading.Event()


def perguntar(texto):
	global prompt_atual
	prompt_atual = texto
	return input(texto)


def receber_arquivo(sock, tamanho):
	os.makedirs(PASTA_DOWNLOADS, exist_ok=True)
	caminho = os.path.join(PASTA_DOWNLOADS, os.path.basename(arquivo_pedido))
	hash_sha = hashlib.sha256()
	recebidos = 0

	print(f"\nRecebendo '{arquivo_pedido}' ({tamanho} bytes)...")

	with open(caminho, "wb") as arquivo:
		while recebidos < tamanho:
			bloco = protocol.receber_bytes(sock, min(protocol.TAMANHO_BLOCO, tamanho - recebidos))

			arquivo.write(bloco)
			hash_sha.update(bloco)
			recebidos += len(bloco)

	print(f"Arquivo salvo em {caminho}")

	return hash_sha.hexdigest()


def receber_mensagens(sock):
	hash_local = ""

	try:
		while True:
			tipo, nome, tam_dados = protocol.receber_inicio(sock)

			if tipo == protocol.Tipo.CHAT_SERVIDOR:
				texto = protocol.receber_bytes(sock, tam_dados).decode("utf-8")
				print(f"\n[{nome}] {texto}")
				print(prompt_atual, end="", flush=True)

			elif tipo == protocol.Tipo.ARQUIVO:
				hash_local = receber_arquivo(sock, tam_dados)

			elif tipo == protocol.Tipo.HASH:
				hash_servidor = protocol.receber_bytes(sock, tam_dados).decode("utf-8")
				print(f"SHA-256 do servidor: {hash_servidor}")
				print(f"SHA-256 local:       {hash_local}")

				if hash_servidor == hash_local:
					print("Integridade OK")
				else:
					print("ERRO: os hashes não batem, arquivo corrompido")

				download_concluido.set()

			elif tipo == protocol.Tipo.ERRO:
				texto = protocol.receber_bytes(sock, tam_dados).decode("utf-8")
				print(f"\nErro ao pedir '{nome}': {texto}")
				download_concluido.set()

			else:
				print(f"\nMensagem inesperada do servidor: {tipo.name}")
				break

	except (ConnectionError, ValueError):
		pass

	print("\nConexão com o servidor encerrada")
	download_concluido.set()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_cliente:

	sock_cliente.connect((HOST, PORT)) 
	print(f"Conectado ao servidor em {HOST}:{PORT}")

	leitora = threading.Thread(target=receber_mensagens, args=(sock_cliente,), daemon=True)
	leitora.start()

	while True:
		print("\n1 - Arquivo\n2 - Chat\n3 - Sair")
		opcao = perguntar("Escolha uma opção: ")

		if not leitora.is_alive():
			break

		if opcao == "1":
			arquivo_pedido = perguntar("Nome do arquivo: ")
			download_concluido.clear()
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.PEDIDO_ARQUIVO, arquivo_pedido, "")
			download_concluido.wait()

		elif opcao == "2":
			texto = perguntar("Mensagem: ")
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.CHAT_CLIENTE, "", texto)

		elif opcao == "3":
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.SAIR, "", "")
			leitora.join()
			break

		else:
			print("Opção inválida")
