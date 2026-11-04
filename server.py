import socket
import threading
import protocol

HOST = "127.0.0.1"
PORT = 65432

clientes = []
lock_clientes = threading.Lock()


def atender_cliente(conexao, endereco):
	with conexao:
		with lock_clientes:
			clientes.append(conexao)
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

				else:
					print(f"{endereco} mandou uma mensagem inesperada: {tipo.name}")
					break

		except (ConnectionError, ValueError) as erro:
			print(f"{endereco} desconectou: {erro}")

		finally:
			with lock_clientes:
				clientes.remove(conexao)
				print(f"{endereco} removido ({len(clientes)} clientes)")


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:

	servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #resolve o problema de Adress alreday in use, mata o TIME_WAIT
	servidor.bind((HOST, PORT))
	
	servidor.listen()
	print(f"Server escutando em {HOST}:{PORT} e aguardando conexões...")

	while True:
		conexao, endereco = servidor.accept()

		thread = threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True)
		thread.start()
