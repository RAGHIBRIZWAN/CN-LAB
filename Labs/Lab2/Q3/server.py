import socket
import threading
import os

server_socket = socket.socket()
server_socket.bind(("localhost", 9997))
server_socket.listen(5)

print("Chat server started. Waiting for connections")

connected_clients = []
allowed_extensions = [".txt", ".jpg", ".pdf"]
banned_words = ["badword", "ugly", "hate"]


def manage_connection(client_conn, client_addr):
    print("Connected with", client_addr)
    connected_clients.append(client_conn)

    while True:
        try:
            data = client_conn.recv(4096)

            if not data:
                break

            decoded_data = data.decode(errors="ignore")

            if decoded_data.startswith("MSG:"):
                message = decoded_data[4:]

                if any(word in message.lower() for word in banned_words):
                    client_conn.send(
                        "⚠ Message rejected due to inappropriate content.".encode()
                    )
                    continue

                print(f"{client_addr} says: {message}")

                for client in connected_clients:
                    if client != client_conn:
                        client.send(
                            f"MSG from {client_addr}: {message}".encode()
                        )

            elif decoded_data.startswith("FILE:"):
                filename = decoded_data[5:].strip()
                extension = os.path.splitext(filename)[1]

                if extension not in allowed_extensions:
                    client_conn.send(
                        "File type not allowed. Only .txt, .jpg, .pdf accepted.".encode()
                    )
                    continue

                client_conn.send("File accepted. Sending...".encode())

                file_data = client_conn.recv(4096)

                with open("received_" + os.path.basename(filename), "wb") as file:
                    file.write(file_data)

                print(f"File received from {client_addr}: {filename}")

                for client in connected_clients:
                    if client != client_conn:
                        client.send(
                            f"File received from {client_addr}: {filename}".encode()
                        )

        except:
            break

    if client_conn in connected_clients:
        connected_clients.remove(client_conn)

    client_conn.close()
    print("Client disconnected:", client_addr)


while True:
    client_socket, client_address = server_socket.accept()
    threading.Thread(target=manage_connection,args=(client_socket, client_address)).start()
