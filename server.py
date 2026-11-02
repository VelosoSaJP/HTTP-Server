import socket
import threading

HOST = "127.0.0.1"
PORT = 65432


def atender_cliente(conexao, endereco):
	with conexao:
		print(f"Conectado: {endereco}")

		while True:
			
			dados = conexao.recv(1024)
			
			if not dados:
				print(f"{endereco} desconectou")
				break

			print(f"{endereco}: {dados.decode()}")
			conexao.sendall(dados)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:

	servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #resolve o problema de Adress alreday in use
	servidor.bind((HOST, PORT))
	
	servidor.listen()
	print(f"Server escutando em {HOST}:{PORT} e aguardando conexões...")

	while True:
		conexao, endereco = servidor.accept()

		thread = threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True)
		thread.start()
