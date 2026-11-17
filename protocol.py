import os
import time


TAMANHO_BLOCO = 8192
TAMANHO_MAX_CABECALHO = 8192
TIMEOUT = 5
NOME_SERVIDOR = "ServidorRedes/1.0"

FRASES_STATUS = {
	200: "OK",
	400: "Bad Request",
	403: "Forbidden",
	404: "Not Found",
}

TIPOS_MIME = {
	".html": "text/html; charset=utf-8",
	".txt": "text/plain; charset=utf-8",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".png": "image/png",
	".ico": "image/x-icon",
}

TIPO_PADRAO = "application/octet-stream"


def receber_requisicao(sock):
	buffer = b""

	while b"\r\n\r\n" not in buffer:
		if len(buffer) > TAMANHO_MAX_CABECALHO:
			raise ValueError("Cabeçalho grande demais")

		pedaco = sock.recv(1024)

		if not pedaco:
			raise ConnectionError("Conexão fechada")

		buffer += pedaco

	cabecalho = buffer.split(b"\r\n\r\n", 1)[0]

	return cabecalho.decode("latin-1")


def interpretar_requisicao(cabecalho):
	linha = cabecalho.split("\r\n", 1)[0]
	partes = linha.split(" ")

	if len(partes) != 3:
		raise ValueError(f"Linha de requisição malformada: {linha!r}")

	metodo, caminho, versao = partes

	if not versao.startswith("HTTP/") or not caminho.startswith("/"):
		raise ValueError(f"Linha de requisição malformada: {linha!r}")

	if metodo != "GET":
		raise ValueError(f"Método não suportado: {metodo}")

	return metodo, caminho, versao


def extrair_nome(caminho):
	nome = caminho.split("?", 1)[0][1:]

	if nome == "":
		return "index.html"

	return nome


def tipo_mime(nome):
	extensao = os.path.splitext(nome)[1].lower()

	return TIPOS_MIME.get(extensao, TIPO_PADRAO)


def montar_cabecalho(status, tipo, tamanho):
	data = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

	linhas = [
		f"HTTP/1.1 {status} {FRASES_STATUS[status]}",
		f"Date: {data}",
		f"Server: {NOME_SERVIDOR}",
		f"Content-Type: {tipo}",
		f"Content-Length: {tamanho}",
		"Connection: close",
	]

	return ("\r\n".join(linhas) + "\r\n\r\n").encode("utf-8")


def enviar_erro(sock, status):
	titulo = f"{status} {FRASES_STATUS[status]}"
	corpo = f"<html>\n <head><title>{titulo}</title></head>\n <body><h1>{titulo}</h1></body>\n</html>\n"
	corpo_bytes = corpo.encode("utf-8")

	sock.sendall(montar_cabecalho(status, "text/html; charset=utf-8", len(corpo_bytes)) + corpo_bytes)
