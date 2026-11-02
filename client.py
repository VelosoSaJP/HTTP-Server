import socket

HOST = "127.0.0.1"
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_cliente:

	sock_cliente.connect((HOST, PORT)) #comeca o handshake com o server
	print(f"Conectado ao servidor em {HOST}:{PORT}")

	while True:
		mensagem = input("Digite uma mensagem (ou 'sair' para encerrar): ")
		if mensagem == "sair":
			break

		sock_cliente.sendall(mensagem.encode())

		resposta = sock_cliente.recv(1024)
		
		if not resposta:
			print("Servidor desconectou")
			break

		print(f"Resposta do servidor: {resposta.decode()}")
