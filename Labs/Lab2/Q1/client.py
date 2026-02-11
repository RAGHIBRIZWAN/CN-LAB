import socket

def start_server():
    server_socket = socket.socket()
    print("Socket created")

    server_socket.bind(("localhost", 9998))
    server_socket.listen(5)

    print("Waiting for connection")

    while True:
        client_socket, client_address = server_socket.accept()
        print("Connected with", client_address)

        while True:
            data = client_socket.recv(1024).decode()

            if data.startswith("MSG:"):
                message = data[4:]  # Extract message after "MSG:"

                if not message or message.lower() == "exit":
                    print("Client disconnected")
                    client_socket.close()
                    break

                print("Client:", message)

                reply = input("Server: ")
                client_socket.send(reply.encode())

                if reply.lower() == "exit":
                    print("Connection closed by server")
                    client_socket.close()
                    break

            elif data.startswith("FILE:"):
                filename = data[5:]  # Extract filename after "FILE:"

                print("Client sent a file named:", filename)

                file_data = client_socket.recv(4096)

                with open(filename, "wb") as file:
                    file.write(file_data)

                reply = input("Server: ")
                client_socket.send(reply.encode())

                if reply.lower() == "exit":
                    print("Connection closed by server")
                    client_socket.close()
                    break

start_server()
