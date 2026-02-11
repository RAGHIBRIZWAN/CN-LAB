import socket
import threading

client_socket = socket.socket()
client_socket.connect(("localhost", 9997))

print("Connected to chat server")

def listen_from_server():
    while True:
        try:
            incoming_message = client_socket.recv(1024).decode()

            if not incoming_message or incoming_message.lower() == "exit":
                print("Server disconnected")
                client_socket.close()
                break

            print("MSG:", incoming_message)

        except:
            break

receiver_thread = threading.Thread(target=listen_from_server)
receiver_thread.start()

while True:
    outgoing_message = input("Client: ")
    client_socket.send(outgoing_message.encode())

    if outgoing_message.lower() == "exit":
        print("Disconnected by client")
        client_socket.close()
        break
