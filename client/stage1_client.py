import socket
import struct
import os
import sys
  
file_name = "sample.mp4"
_, ext = os.path.splitext(file_name) # 拡張子を取得する

if ext.lower() != ".mp4":
    print(f"エラー: 送信しようとしたファイル（{file_name}）は MP4 形式ではありません。")
    print("このプログラムは MP4 のみをサポートしています。処理を中断します。")
    sys.exit(1) # 異常は1

file_size = os.path.getsize(file_name)

# ▫️仕様 32バイトのヘッダー
HEADER_SIZE = 32
PACKED_SIZE = 4 # ファイルサイズ 4GB = 4バイト = 2 ** 32
PADDING_SIZE = HEADER_SIZE - PACKED_SIZE # 余白分

header_padding = b"\x00" * PADDING_SIZE
fixed_header = struct.pack("!I", file_size) + header_padding

SEVER_IP = "127.0.0.1"
PORT = 8080
address = (SEVER_IP, PORT)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(address)
print(f"サーバ {address} に接続しました。")

try:
    client_socket.sendall(fixed_header)
    print(f"固定ヘッダー（32バイト）を送信しました。")

    with open(file_name, "rb") as f:
        while True:
            chunk = f.read(1400)
            if not chunk:
                break
            client_socket.sendall(chunk)
    print("動画ファイル本体の送信が完了しました！")

    response_bytes = client_socket.recv(16)
    print("サーバからのフィードバック（16バイト）を受信しました。")
    
    status_info, = struct.unpack("!I", response_bytes[:4]) # struct.unpack()はタプルを返す

    if status_info == 1:
        print("【成功】サーバ側で動画ファイルが正常に保存されました！")
    else:
        print(f"【警告】サーバからい異常なステータス({status_info})")

finally:
    client_socket.close
    print("ソケットを閉じました。")