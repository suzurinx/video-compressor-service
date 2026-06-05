import socket
import struct

HEADER_SIZE = 32
HEADER_FORMAT = "!I"
PACKED_SIZE = 4

SERVER_IP = "127.0.0.1"
PORT = 8080
address = (SERVER_IP, PORT)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(address)
server_socket.listen(1)

print(f"サーバが起動しました。{address[0]} : {address[1]} で接続を待っています。")


try:
    client_socket, client_address = server_socket.accept()
    print(f"クライアントが接続してきました！ 相手の住所: {client_address}")

    header_bytes = client_socket.recv(HEADER_SIZE)
    print("固定ヘッダーを受信しました。")

    file_size, = struct.unpack(HEADER_FORMAT, header_bytes[:PACKED_SIZE])
    print(f"【解剖結果】ファイルサイズ: {file_size}バイト")

    save_name = "received_video.mp4"
    with open(save_name, "wb") as f:
        received_bytes = 0

        while received_bytes < file_size:
            left_bytes = file_size - received_bytes
            buffer_size = min(4096, left_bytes)

            chunk = client_socket.recv(buffer_size)
            if not chunk:
                break

            f.write(chunk)
            received_bytes += len(chunk)
    
    print(f"動画ファイル本体の受信が完了しました！ '{save_name}' として保存しました。")

    # レスポンスプロトコル 16バイト
    status_info = 1
    packed_status = struct.pack("!I", status_info)
    response_padding = b"\00" * 12
    response_message = packed_status + response_padding

    client_socket.sendall(response_message)
    print("クライアントに正常終了のフィードバックをしました。")

finally:
    server_socket.close()
    print("ソケットを閉じました。")