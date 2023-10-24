import socket
import threading
import cv2
import numpy as np
import os
import pyaudio
import pyautogui

# Chat client setup
nick = input("Enter a nickname: ")
chat_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
chat_IP_ADDR = socket.gethostbyname(socket.gethostname())
chat_port = 1234
chat_client.connect((chat_IP_ADDR, chat_port))

def send_chat_message():
    while True:
        try:
            message = input()
            chat_client.send(f"{nick}: {message}".encode())
        except:
            chat_client.close()
            break

def receive_chat_message():
    while True:
        try:
            message = chat_client.recv(1024).decode()
            print(message)
        except:
            chat_client.close()
            break

chat_receive_thread = threading.Thread(target=receive_chat_message)
chat_send_thread = threading.Thread(target=send_chat_message)
chat_receive_thread.start()
chat_send_thread.start()

# Video client setup
video_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_client.connect((chat_IP_ADDR, 4444))

def receive_video_stream():
    while True:
        frame_size_bytes = video_client.recv(8)
        frame_size = int.from_bytes(frame_size_bytes, byteorder='big')
        frame_data = b''
        while len(frame_data) < frame_size:
            chunk = video_client.recv(frame_size - len(frame_data))
            if not chunk:
                break
            frame_data += chunk
        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        cv2.imshow('Client - Webcam Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    video_client.close()
    cv2.destroyAllWindows()

video_thread = threading.Thread(target=receive_video_stream)
video_thread.start()

# Screen sharing client setup
screen_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
screen_client.connect((chat_IP_ADDR, 5555))

def send_screen_sharing():
    while True:
        screen = pyautogui.screenshot()
        frame = np.array(screen)
        _, jpeg_frame = cv2.imencode('.jpg', frame)
        screen_client.sendall(len(jpeg_frame).to_bytes(8, byteorder='big'))
        screen_client.sendall(jpeg_frame.tobytes())
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    screen_client.close()

screen_thread = threading.Thread(target=send_screen_sharing)
screen_thread.start()

# Audio client setup
audio_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
audio_client.connect((chat_IP_ADDR, 6666))

def send_audio_stream():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    while True:
        data = stream.read(1024)
        audio_client.sendall(data)
    stream.stop_stream()
    stream.close()
    p.terminate()
    audio_client.close()

audio_thread = threading.Thread(target=send_audio_stream)
audio_thread.start()

# File client setup
file_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
file_client.connect((chat_IP_ADDR, 1235))

def receive_folder_contents(client, output_folder):
    while True:
        file_path = client.recv(1024).decode('utf-8')
        if not file_path:
            break
        if file_path == 'EOF':
            break
        file_data = b''
        while True:
            data = client.recv(1024)
            if not data or data == b'EOF':
                break
            file_data += data
        file_path = os.path.join(output_folder, file_path.replace('\\', '/'))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(file_data)

def send_folder(folder_path):
    file_client.send(folder_path.encode('utf-8'))
    receive_folder_contents(file_client, 'output_folder')
    file_client.close()

folder_path = '/path/to/folder'
file_thread = threading.Thread(target=send_folder, args=(folder_path,))
file_thread.start()
