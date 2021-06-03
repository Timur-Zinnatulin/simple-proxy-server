import socket
from threading import Thread

#Class for HTTP requests
class Request:
    def __init__(self, orig: bytes):
        self.original = orig

        self.headers = {}
        self.bytes = b''
        self.meta = ''

        self.host = None
        self.port = None

    @classmethod
    #Converts byte sequence into an instance of Request class
    def parse(cls, request: bytes):
        request_instance = cls(orig=request)

        http_parts = request.split(b"\r\n\r\n")
        http_head = http_parts[0].split(b"\r\n")
        request_instance.meta = http_head[0].decode("utf-8")
        http_head = http_head[1:]

        if len(http_parts) >= 2:
            request_instance.bytes = http_parts[1]

        # Assign header values
        for header in http_head:
            key, value = header.split(b": ")
            request_instance.headers[key.decode("utf-8")] = value.decode("utf-8")

        # Get host and port
        if ':' in request_instance.headers['Host']:
            host, port = request_instance.headers['Host'].split(':')
        else:
            # Standart port if not specified
            host, port = request_instance.headers['Host'], 80

        request_instance.host = host
        request_instance.port = int(port)

        return request_instance

class ProxyServer:
    def __init__(self, host="0.0.0.0", port=2874):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer = 2048

    def run(self):
        self.client_socket.bind((self.host, self.port))
        self.client_socket.listen(15)
        print(f"Proxy server is running on {self.host}:{self.port}")

        while True:
            client, addr = self.client_socket.accept()
            print(f"Connection accepted from {addr[0]}:{addr[1]}")
            Thread(target=self.handle_request, args=(client,)).start()

    def handle_request(self, client):
        request = Request.parse(client.recv(self.buffer))
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if 'CONNECT' in request.meta:
            self.handle_https_request(request, client, server)
        else:
            self.handle_http_request(request, client, server)

    def handle_http_request(self, request, client, server):
        server.connect((request.host, request.port))
        server.sendall(request.original)

        response = server.recv(self.buffer)
        try:
            parsed_response = Request.parse(response)
            while len(response) < parsed_response.headers['Content-Length']:
                response += server.recv(self.buffer)
        except:
            while not response.endswith(b'0\r\n\r\n'):
                chunk = server.recv(self.buffer)
                response += chunk

        client.sendall(response)

        server.close()
        client.close()

    def handle_https_request(self, request, client, server):
        try:
            server.connect((request.host, request.port))
            reply = "HTTP/1.1 200 Connection Established\r\nProxy-Agent: simple-proxy-server\r\n\r\n"
            client.sendall(reply.encode())
        except socket.error as error:
            print(error)

        client.setblocking(False)
        server.setblocking(False)
        while True:
            try:
                data = client.recv(self.buffer)
                if not data:
                    client.close()
                    break
                server.sendall(data)
            except socket.error:
                pass

            try:
                reply = server.recv(self.buffer)
                if not reply:
                    server.close()
                    break
                client.sendall(reply)
            except socket.error:
                pass

proxy = ProxyServer()
proxy.run()