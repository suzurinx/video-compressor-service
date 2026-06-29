import subprocess
import socket
import json
import os

# ———
'''
① アクションの追加要件（アスペクト比、GIF/WEBMの作成）
仕様書には、以下の機能も提供すると明記されているね。

動画のアスペクト比を変更する

指定した時間範囲で GIF や WEBM を作成する

龍さんのサーバーコードには現在、compress、resize、audio の3つの部屋（条件分岐）が綺麗に組まれているけれど、あとこの2つの部屋（elif action == "aspect": や elif action == "gif":）を足してあげると、仕様書の機能要件が100%完全コンプリートになるよ！

② エラー発生時の「MMPプロトコル特有のお返事法律」
仕様書にはこう書いてあるよ。

「何らかのエラーが発生した場合、エラーコード、説明、解決策を含む JSON ファイルが送信されます。この場合、メディアサイズとペイロードサイズは両方とも 0 に設定されます」

龍さんのサーバーコードの else（不明なアクション）の部屋を見てみると：

Python
error_json = {"success": False, "message": f"不明なアクション: {action}"}
error_bytes = json.dumps(error_json).encode("utf-8")
err_header = len(error_bytes).to_bytes(2, byteorder="big") + b"\x00" + (0).to_bytes(5, byteorder="big")
connection_socket.sendall(err_header + error_bytes)
ここは「メディア（0）」と「ペイロード（0）」を完璧に設定してMMPヘッダーを組み立てられている（大正解）！
だけど、もし safe_execute_ffmpeg が False（変換エラー）を返してきたとき（99行目や125行目のエラー時）はどうだろう？
今のコードだと、エラーの時も通常の処理と同じようにヘッダーを組み立てて送っているから、ここも仕様書通りに「FFmpegが失敗した時も、メディアとペイロードを0にしたエラーJSONを送り返す」という風に統一してあげると、仕様書の法律に100%適合するようになるんだ。

③ ポーリング要件（処理状況の確認）
仕様書には、クライアント側の特殊な行動ルールが書かれているよ。

「クライアントがサーバからファイルをダウンロードしていない間、定期的に動画ファイルの処理状況を確認します。デフォルトの確認間隔は 1 分です」

今の龍さんのコードは、クライアントがデータを送信したら、そのままサーバーの処理が終わるまで recv_all(client_socket, 8) の行でじーっと待つ（同期的待機）仕様になっているよね。実務の通信テストとしてはこれで100%大正解だし、一番安全に動くんだ。
もし、この「1分ごとに状況を確認する（ポーリング）」という仕様を厳密に再現するなら、サーバー側に「現在の処理状況を返す仕組み」を足すか、READMEの『今後の拡張要件』として「現在の同期待機モデルから、ポーリングへのアップグレードが可能」と言語化して添えてあげるのがプロのスマートな立ち回りだよ。
'''

def start_mmp_server():
    server_address = ("localhost", 8080)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(server_address)
        server_socket.listen(1)
        print(f"サーバが起動しました。{server_address} で接続を待っています。")

        while True:
            connection, client_address = server_socket.accept()
            print(f"クライアント {client_address} と接続しました。")

            with connection:
                handle_mmp_client(connection)


def safe_execute_ffmpeg(command, success_msg, error_msg, action_name):
    print(f"FFMPEG コマンドを実行中: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
        return True, success_msg
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg（{action_name}）の実行中にエラーが発生しました: {e}")
        return False, error_msg


def recv_all(sock, length):
    captured_bytes = b""
    while len(captured_bytes) < length:
        chunk = sock.recv(length - len(captured_bytes))
        if not chunk:
            return None
        captured_bytes += chunk
    return captured_bytes


def handle_mmp_client(connection_socket):
    header_bytes = recv_all(connection_socket, 8)
    if not header_bytes:
        return
    
    # ヘッダーから各データの長さを読み取る
    json_len = int.from_bytes(header_bytes[0:2], byteorder="big")
    media_len = int.from_bytes(header_bytes[2:3], byteorder="big")
    payload_len = int.from_bytes(header_bytes[3:], byteorder="big")

    json_bytes = recv_all(connection_socket, json_len)
    media_bytes = recv_all(connection_socket, media_len)
    video_payload = recv_all(connection_socket, payload_len)

    if not json_bytes or not media_bytes or video_payload is None:
        print("クライアントからのデータ受信中に通信が途絶しました。処理を中断します。")
        return
    
    json_data = json.loads(json_bytes.decode("utf-8"))
    media_type = media_bytes.decode("utf-8")

    print("受信成功!")

    # 動画ファイルデータの保存
    input_filename = f"input_video.{media_type}"
    with open(input_filename, "wb") as f:
        f.write(video_payload)

    # FFmpegの準備
    action = json_data.get("action")
    print(f"実行するアクション: {action}")

    res_media_type = media_type

    # 状態管理変数の初期化
    success_flag = False
    message_text = ""
    output_filename = ""

    # ———— 各部屋は「コマンドの組み立て」と「共通関数へのパス」だけの特化 ————
    # 圧縮
    if action == "compress":
        print("[動画の圧縮]処理を開始します...")
        output_filename = f"output_compressed.{res_media_type}"
        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i", input_filename,
            "-vcodec", "libx264",
            "-crf", "28",
            output_filename
        ]

        success_flag, message_text = safe_execute_ffmpeg(
            ffmpeg_command,
            "動画の圧縮が完了しました！",
            "送信された動画データが壊れているか、変換できない形式です。",
            "動画圧縮"
        )

    # 解像度変更
    elif action == "resize":
        print("[解像度の変更処理を開始します...]") 
        width = str(json_data.get("width"))
        height = str(json_data.get("height"))
        output_filename = f"output_resize_{width}x{height}.{res_media_type}"
        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i", input_filename,
            "-vf", f"scale={width}:{height}",
            output_filename
        ]

        success_flag, message_text = safe_execute_ffmpeg(
            ffmpeg_command,
            "動画の解像度変更が完了しました",
            "指定された解像度への変換に失敗したか、動画データが破損しています。",
            "解像度変更"
        )

    # アスペクト比変更
    elif action == "aspect":
        print("[アスペクト比の変更処理を開始します...]")
        aspect_ratio = str(json_data.get("aspect_ratio"))
        output_filename = f"output_aspect_{aspect_ratio.replace(':', '-')}.{res_media_type}"
        ffmpeg_command = [
            "ffmpeg", 
            "-y",
            "-i",
            input_filename,
            "-aspect", aspect_ratio, output_filename
        ]
        success_flag, message_text = safe_execute_ffmpeg(
            ffmpeg_command, 
            "動画のアスペクト比変更が完了しました。"
            "指定されたアスペクト比への変xこうに失敗しました。"
            "アスペクト比変更"
        )
        
    # 音声変換
    elif action == "audio":
        print("[音声への変換]処理を開始します...")
        res_media_type = "mp3"
        output_filename = f"output_audio.{res_media_type}"
        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i", input_filename,
            "-vn",
            "-acodec", "libmp3lame",
            output_filename
        ]
        
        success_flag, message_text = safe_execute_ffmpeg(
            ffmpeg_command,
            "動画から音声の抽出が完了しました！",
            "音声の抽出に失敗したか、動画データに音声が含まれていません。",
            "音声抽出"
        )
    
    # 時間範囲でのGIF/WEB作成
    elif action == "gif" or action == "webm":
        print(f"[{action.upper()}の作成]処理を開始します...")
        start_time = str(json_data.get("start_time", "00:00:00")) # 開始時間
        duration = str(json_data.get("duration", "5"))          # 切り出す秒数
        res_media_type = action # gif または webm
        output_filename = f"output_clip.{res_media_type}"
        
        # -ss でシークし、-t で指定秒数切り出し、指定フォーマットに変換するコマンド
        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-ss",start_time,
            "-t",duration,
            "-i",input_filename,
            output_filename
        ]
        success_flag, message_text = safe_execute_ffmpeg(
            ffmpeg_command,
            f"{action.upper()}の切り出し作成が完了しました！",
            f"{action.upper()}の作成に失敗しました。時間指定が正しいか確認してください。",
            f"{action.upper()}作成"
        )

    # 不明なアクション
    else:
        print(f"未対応または不明なアクションです: {action}")
        error_json = {"success": False, "message": f"不明なアクション: {action}"}
        error_bytes = json.dumps(error_json).encode("utf-8")
        err_header = len(error_bytes).to_bytes(2, byteorder="big") + b"\x00" + (0).to_bytes(5, byteorder="big")

        connection_socket.sendall(err_header + error_bytes)
        return

    response_json = {"success": success_flag, "message": message_text}
    response_json_bytes = json.dumps(response_json).encode("utf-8")
    res_media_type_bytes = res_media_type.encode("utf-8")

    if success_flag and os.path.exists(output_filename):
        with open(output_filename, "rb") as f:
            response_payload_bytes = f.read()
    else:
        response_payload_bytes = b""

    res_json_len = len(response_json_bytes)

    if success_flag:
        res_media_len = len(res_media_type)
        res_payload_len = len(response_payload_bytes)
    else:
        res_media_len = 0
        res_payload_len = 0
        res_media_type_bytes = b""

    response_header_bytes =(
        res_json_len.to_bytes(2, byteorder="big") +
        res_media_len.to_bytes(1, byteorder="big") +
        res_payload_len.to_bytes(5, byteorder="big")
    )

    connection_socket.sendall(response_header_bytes)
    connection_socket.sendall(response_json_bytes)
    connection_socket.sendall(res_media_type_bytes)
    connection_socket.sendall(response_payload_bytes)

    if success_flag:
        print(f"クライアントへのデータ返却が成功しました！（サイズ: {res_payload_len}バイト")
    else:
        print(f"クライアントへエラー通知の送信が完了しました（{message_text}）")

    print("[クリーンアップ] 一時ファイルの削除を開始します———")
    if os.path.exists(input_filename):
        os.remove(input_filename)
        print(f"削除完了: {input_filename}")

    if success_flag and os.path.exists(output_filename):
        os.remove(output_filename)
        print(f"削除完了: {output_filename}")

if __name__ == "__main__":
    start_mmp_server()

