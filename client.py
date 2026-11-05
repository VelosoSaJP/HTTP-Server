import socket
import threading
import protocol

HOST = "127.0.0.1"
PORT = 65432

prompt_atual = ""


def perguntar(texto):
	global prompt_atual
	prompt_atual = texto
	return input(texto)


def receber_mensagens(sock):
	try:
		while True:
			tipo, nome, tam_dados = protocol.receber_inicio(sock)

			if tipo == protocol.Tipo.CHAT_SERVIDOR:
				texto = protocol.receber_bytes(sock, tam_dados).decode("utf-8")
				print(f"\n[{nome}] {texto}")
				print(prompt_atual, end="", flush=True)

			else:
				print(f"\nMensagem inesperada do servidor: {tipo.name}")
				break

	except (ConnectionError, ValueError):
		pass

	print("\nConexão com o servidor encerrada")


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_cliente:

	sock_cliente.connect((HOST, PORT)) #comeca o handshake com o server
	print(f"Conectado ao servidor em {HOST}:{PORT}")

	leitora = threading.Thread(target=receber_mensagens, args=(sock_cliente,), daemon=True)
	leitora.start()

	while True:
		print("\n1 - Chat\n2 - Sair")
		opcao = perguntar("Escolha uma opção: ")

		if not leitora.is_alive():
			break

		if opcao == "1":
			texto = perguntar("Mensagem: ")
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.CHAT_CLIENTE, "", texto)

		elif opcao == "2":
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.SAIR, "", "")
			leitora.join()
			break

		else:
			print("Opção inválida")
