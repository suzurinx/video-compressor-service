import socket
import struct
import os
import sys
  
file_name = "sample.mp4"
_, ext = os.path.splitext(file_name)

if ext.lower() != ".mp4":
    print(f"エラー: 送信しようとしたファイル（{file_name}）は MP4 形式ではありません。")
    sys.exit(1)

# 1. 仕様書通り、最大4GBまでのファイルサイズ（4バイト分）を取得
file_size = os.path.getsize(file_name)

# 2. 仕様書通り「最初の32バイト」のヘッダーを作る
HEADER_SIZE = 32
PACKED_SIZE = 4  # ファイルサイズ（4GB = 32ビット符号なし整数 = 4バイト）
PADDING_SIZE = HEADER_SIZE - PACKED_SIZE

header_padding = b"\x00" * PADDING_SIZE
# "!I" で4バイトの整数をパッキングし、残り28バイトを埋めて合計32バイトにする
fixed_header = struct.pack("!I", file_size) + header_padding

SERVER_IP = "127.0.0.1"
PORT = 8080
address = (SERVER_IP, PORT)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(address)
print(f"サーバ {address} に接続しました。")

try:
    # 最初の32バイトを送信（仕様書通り）
    client_socket.sendall(fixed_header)
    print("ファイルのバイト数を含むヘッダー（32バイト）を送信しました。")

    # 動画ファイル本体を1400バイトずつ送信（仕様書通り）
    with open(file_name, "rb") as f:
        while True:
            chunk = f.read(1400)
            if not chunk:
                break
            client_socket.sendall(chunk)
    print("動画ファイル本体の送信が完了しました！")

    # サーバーからのレスポンス（16バイト）を受信（仕様書通り）
    response_bytes = client_socket.recv(16)
    status_info, = struct.unpack("!I", response_bytes[:4])

    if status_info == 1:
        print("【大成功】サーバ側で動画ファイルが正常に保存されました！")
    else:
        print(f"【警告】サーバから異常なステータス({status_info})が返されました。")

finally:
    client_socket.close()
    print("ソケットを閉じました。")