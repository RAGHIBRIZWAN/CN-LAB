import socket
import threading
import os

client_socket = socket.socket()
client_socket.connect(("localhost", 9997))

print("Connected to chat server")

def listen_from_server():
    while True:
        try:
            data = client_socket.recv(4096).decode()

            if not data or data.lower() == "exit":
                print("Server disconnected")
                client_socket.close()
                break

            print(data)

        except:
            break


receiver_thread = threading.Thread(target=listen_from_server)
receiver_thread.start()

while True:
    choice = input("Send message (m) or file (f)?: ").lower()

    if choice == "m":
        message = input("Client: ")
        client_socket.send(f"MSG:{message}".encode())

        if message.lower() == "exit":
            print("Disconnected by client")
            client_socket.close()
            break

    elif choice == "f":
        filename = input("Enter file name: ")

        if not os.path.exists(filename):
            print("File does not exist")
            continue

        client_socket.send(f"FILE:{filename}".encode())

        with open(filename, "rb") as file:
            client_socket.send(file.read())

    else:
        print("Invalid option")
