import socket
import json
import os


def recv_all(sock, length):
    captured_bytes = b""
    while len(captured_bytes) < length:
        chunk = sock.recv(length - len(captured_bytes))
        if not chunk:
            return None
        captured_bytes += chunk
    return captured_bytes


def start_mmp_client():
    server_address = ("localhost", 8080)
    input_video_path = "sample.mp4"  # 送信するテスト動画ファイル

    if not os.path.exists(input_video_path):
        print(f"エラー: 送信用テスト動画 '{input_video_path}' が見つかりません。")
        return

    # 課題要件の指示書（JSON）の組み立てフェーズ
    # テストしたいアクションに合わせて、ここのコメントアウトを切り替えて提出・テストできます
    
    # パターンA：動画圧縮 (compress)
    json_data = {"action": "compress"}
    
    # パターンB：解像度変更 (resize)
    # json_data = {"action": "resize", "width": 1280, "height": 720}
    
    # パターンC：アスペクト比変更 (aspect)
    # json_data = {"action": "aspect", "aspect_ratio": "16:9"}
    
    # パターンD：音声抽出 (audio)
    # json_data = {"action": "audio"}
    
    # パターンE：時間切り出し (gif / webm)
    # json_data = {"action": "gif", "start_time": "00:00:02", "duration": "3"}

    # メディア（拡張子）の抽出
    media_type = input_video_path.split(".")[-1]

    # バイナリデータの準備
    json_bytes = json.dumps(json_data).encode("utf-8")
    media_bytes = media_type.encode("utf-8")
    with open(input_video_path, "rb") as f:
        video_payload_bytes = f.read()

    # 各パーツの長さを計測
    json_len = len(json_bytes)
    media_len = len(media_bytes)
    payload_len = len(video_payload_bytes)

    # MMPヘッダーのパッキング (2バイト + 1バイト + 5バイト = 8バイト)
    header_bytes = (
        json_len.to_bytes(2, byteorder="big") +
        media_len.to_bytes(1, byteorder="big") +
        payload_len.to_bytes(5, byteorder="big")
    )

    print(f"{server_address} のサーバに接続を試みます...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(server_address)
        print("接続成功！ データをMMPプロトコルで送信します...")

        # 往路：一気にサーバへ発射！
        client_socket.sendall(header_bytes)
        client_socket.sendall(json_bytes)
        client_socket.sendall(media_bytes)
        client_socket.sendall(video_payload_bytes)
        print("送信完了。サーバー側での動画調理とお返事を待っています...")

        # 復路：サーバーからの加工完了パケットの回収開始
        res_header_bytes = recv_all(client_socket, 8)
        if not res_header_bytes:
            print("サーバーから応答ヘッダーを受け取れませんでした。")
            return

        # サーバーから届いたヘッダーを解剖
        res_json_len = int.from_bytes(res_header_bytes[0:2], byteorder="big")
        res_media_len = int.from_bytes(res_header_bytes[2:3], byteorder="big")
        res_payload_len = int.from_bytes(res_header_bytes[3:], byteorder="big")

        # 3つのデータを確実に回収
        res_json_bytes = recv_all(client_socket, res_json_len)
        
        # 課題要件シンクロ：もしペイロード長（またはメディア長）が0なら、それはサーバー側での処理エラーを意味する！
        if res_media_len == 0 or res_payload_len == 0:
            print("\n 【MMPエラープロトコルを検知しました】")
            if res_json_bytes:
                error_info = json.loads(res_json_bytes.decode("utf-8"))
                print(f"エラー内容: {error_info.get('message')}")
            print("仕様書に基づき、処理を安全に終了します。")
            return

        # 正常系の場合のみ、残りの拡張子と動画バイナリを回収
        res_media_bytes = recv_all(client_socket, res_media_len)
        res_payload_bytes = recv_all(client_socket, res_payload_len)

        if not res_json_bytes or not res_media_bytes or res_payload_bytes is None:
            print("サーバーからのデータ回収中に通信が途絶しました。")
            return

        # データのデコード
        response_json_data = json.loads(res_json_bytes.decode("utf-8"))
        result_media_type = res_media_bytes.decode("utf-8")

        print("\n--- サーバーからのリプライ ---")
        print(f"ステータス: {response_json_data.get('success')}")
        print(f"メッセージ: {response_json_data.get('message')}")

        # 処理済みデータの保存処理
        output_filename = f"client_received_result.{result_media_type}"
        with open(output_filename, "wb") as f:
            f.write(res_payload_bytes)

        print(f" すべての工程が完了しました！")
        print(f"成果物が '{output_filename}' として安全に保存されました。(サイズ: {len(res_payload_bytes)}バイト)")


if __name__ == "__main__":
    start_mmp_client()