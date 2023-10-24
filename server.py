import socket
import threading
import cv2
import os
import pyaudio
import numpy as np


# Chat server setup
chat_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
chat_IP_ADDR = socket.gethostbyname(socket.gethostname())
chat_port = 1234
chat_server.bind((chat_IP_ADDR, chat_port))
chat_server.listen()

# Video server setup
video_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_server.bind((chat_IP_ADDR, 4444))
video_server.listen()

# Screen sharing server setup
screen_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
screen_server.bind((chat_IP_ADDR, 5555))
screen_server.listen()

# Audio server setup
audio_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
audio_server.bind((chat_IP_ADDR, 6666))
audio_server.listen()

# File server setup
file_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
file_server.bind((chat_IP_ADDR, 1235))
file_server.listen()

print(f"Chat Server is listening on {chat_IP_ADDR}:{chat_port}")
print(f"Video Server is listening on {chat_IP_ADDR}:4444")
print(f"Screen Sharing Server is listening on {chat_IP_ADDR}:5555")
print(f"Audio Server is listening on {chat_IP_ADDR}:6666")
print(f"File Server is listening on {chat_IP_ADDR}:1235")

clients = []
nicknames = []

def broadcast(message, sender_client):
    for client in clients:
        if client != sender_client:
            client.send(message.encode('utf-8'))

def handle_client(client):
    while True:
        try:
            message = client.recv(1024).decode()
            broadcast(message, client)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f"{nickname} has left the chat.", client)
            nicknames.remove(nickname)
            break

def accept_chat_clients():
    while True:
        client, address = chat_server.accept()
        print(f"Chat connection received from {address}")

        client.send("NICK?".encode())
        nick = client.recv(1024).decode()
        clients.append(client)
        nicknames.append(nick)
        print(f"Nickname of the client is {nick}")

        client.send("You are connected to the chat server".encode())
        broadcast(f"{nick} has joined the chat.", client)

        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

def handle_video_stream(client):
    webcam = cv2.VideoCapture(0)
    while True:
        ret, frame = webcam.read()
        if not ret:
            break
        cv2.imshow('Server - Webcam Stream', frame)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, jpeg_frame = cv2.imencode('.jpg', frame, encode_param)
        client.sendall(len(jpeg_frame).to_bytes(8, byteorder='big'))
        client.sendall(jpeg_frame.tobytes())
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    webcam.release()
    cv2.destroyAllWindows()
    client.close()

def accept_video_clients():
    while True:
        client, address = video_server.accept()
        print(f"Video connection received from {address}")
        thread = threading.Thread(target=handle_video_stream, args=(client,))
        thread.start()

def handle_screen_sharing(client):
    while True:
        frame_size_bytes = client.recv(8)
        frame_size = int.from_bytes(frame_size_bytes, byteorder='big')
        frame_data = b''
        while len(frame_data) < frame_size:
            chunk = client.recv(frame_size - len(frame_data))
            if not chunk:
                break
            frame_data += chunk
        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        cv2.imshow('Server - Screen Sharing', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    client.close()
    cv2.destroyAllWindows()

def accept_screen_clients():
    while True:
        client, address = screen_server.accept()
        print(f"Screen sharing connection received from {address}")
        thread = threading.Thread(target=handle_screen_sharing, args=(client,))
        thread.start()

def handle_audio_stream(client):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)
    while True:
        try:
            data = client.recv(1024)
            stream.write(data)
        except:
            break
    stream.stop_stream()
    stream.close()
    p.terminate()
    client.close()

def accept_audio_clients():
    while True:
        client, address = audio_server.accept()
        print(f"Audio connection received from {address}")
        thread = threading.Thread(target=handle_audio_stream, args=(client,))
        thread.start()

def send_folder_contents(client, folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, folder_path)
            client.sendall(relative_path.encode('utf-8'))
            with open(file_path, 'rb') as f:
                file_data = f.read()
                client.sendall(file_data)
            client.sendall(b'EOF')

def handle_file_transfer(client):
    folder_path = client.recv(1024).decode('utf-8')
    send_folder_contents(client, folder_path)
    client.close()

def accept_file_clients():
    while True:
        client, address = file_server.accept()
        print(f"File connection received from {address}")
        thread = threading.Thread(target=handle_file_transfer, args=(client,))
        thread.start()

if __name__ == "__main__":
    threading.Thread(target=accept_chat_clients).start()
    threading.Thread(target=accept_video_clients).start()
    threading.Thread(target=accept_screen_clients).start()
    threading.Thread(target=accept_audio_clients).start()
    threading.Thread(target=accept_file_clients).start()
