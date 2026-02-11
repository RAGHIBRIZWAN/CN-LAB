import socket

def start_client():
    client_socket = socket.socket()
    client_socket.connect(("localhost", 9998))

    print("Connected to server")

    while True:
        user_choice = input("Send message (m/M) or file (f/F)?: ").strip()
        client_socket.send(user_choice.encode())

        if user_choice.lower() == "m":
            message = input("Client: ")
            client_socket.send(f"MSG: {message}".encode())

            if message.lower() == "exit":
                print("Disconnected from server")
                client_socket.close()
                break

            server_reply = client_socket.recv(1024).decode()

            if not server_reply or server_reply.lower() == "exit":
                print("Server ended the chat")
                client_socket.close()
                break

            print("Server:", server_reply)

        elif user_choice.lower() == "f":
            file_name = input("Enter filename: ")
            client_socket.send(f"FILE: {file_name}".encode())

            try:
                with open(file_name, "rb") as file:
                    file_data = file.read()
                    client_socket.send(file_data)
                print("File sent successfully")

            except FileNotFoundError:
                print("File not found.")
                continue

            server_reply = client_socket.recv(1024).decode()
            print("Server:", server_reply)

            if server_reply.lower() == "exit":
                print("Disconnected from server")
                client_socket.close()
                break

        else:
            print("Invalid option.")

start_client()
