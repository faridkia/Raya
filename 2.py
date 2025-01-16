def handle_tcp():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 5001))
    server.listen(5)
    print("TCP server listening...")
    while True:
        conn, addr = server.accept()
        message = conn.recv(1024).decode()
        response = message_process(message)
        conn.sendall(response.encode())

def handle_udp():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('127.0.0.1', 5002))
    print("UDP server listening...")
    while True:
        message, addr = server.recvfrom(1024)
        response = message_process(message.decode())
        server.sendto(response.encode(), addr)