import socket
import threading

server_socket = socket.socket()
print("Socket created")

server_socket.bind(("localhost", 9997))
server_socket.listen(5)

print("Waiting for connections")

connected_clients = [] 

def manage_connection(client_conn, client_addr):
    print("Connected with", client_addr)
    connected_clients.append(client_conn)

    while True:
        try:
            received_text = client_conn.recv(1024).decode()

            if not received_text or received_text.lower() == "exit":
                print("Client disconnected:", client_addr)
                connected_clients.remove(client_conn)
                client_conn.close()
                break

            print(f"{client_addr} says:", received_text)

            for active_client in connected_clients:
                if active_client != client_conn:
                    active_client.send(
                        f"MSG from {client_addr}: {received_text}".encode()
                    )

        except:
            if client_conn in connected_clients:
                connected_clients.remove(client_conn)
            client_conn.close()
            break

while True:
    new_client, new_address = server_socket.accept()
    threading.Thread(target=manage_connection,args=(new_client, new_address)).start()
