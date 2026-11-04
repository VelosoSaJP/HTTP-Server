import socket
import protocol

HOST = "127.0.0.1"
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_cliente:

	sock_cliente.connect((HOST, PORT)) #comeca o handshake com o server
	print(f"Conectado ao servidor em {HOST}:{PORT}")

	while True:
		print("\n1 - Chat\n2 - Sair")
		opcao = input("Escolha uma opção: ")

		if opcao == "1":
			texto = input("Mensagem: ")
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.CHAT_CLIENTE, "", texto)

		elif opcao == "2":
			protocol.enviar_mensagem(sock_cliente, protocol.Tipo.SAIR, "", "")
			break

		else:
			print("Opção inválida")
