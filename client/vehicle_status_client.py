"""
車両ステータス通知クライアント (SOME/IP) - スケルトン
======================================================
演習参加者向け実装テンプレート

【課題】
  このスケルトンの TODO 箇所を実装し、要件仕様書 (SRS-VSCL-001) を
  満たすクライアントアプリケーションを完成させてください。

【使い方】
  python vehicle_status_client.py [--host HOST] [--port PORT] [--server-port PORT]

【参照ドキュメント】
  - docs/01_SWE1_software_requirements_spec.md (要件仕様書)
  - docs/02_SWE2_SWE3_interface_spec.md (インターフェース仕様書)
  - server/someip_common.py (共通モジュール - 利用可)
"""

import argparse
import asyncio
import logging
import signal
import socket
import struct
import sys
import time
from pathlib import Path

# --- 共通モジュールのインポート ---
# someip_common.py を利用できます。サーバと同じディレクトリ構成を前提としています。
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
from someip_common import (
    SomeIpHeader, MessageType, ReturnCode,
    VEHICLE_STATUS_SERVICE_ID, VehicleStatusMethodId,
    VehicleStatus, DiagnosticInfo,
    AlertMessage, AlertType, ALERT_METHOD_ID,
    HEADER_SIZE,
)

# ==============================================================================
# ロガー設定
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VehicleClient")


# ==============================================================================
# アラート閾値定義
# ==============================================================================
# SRS-FUNC-020〜023 を参照して閾値を定義してください

SPEED_WARNING_THRESHOLD = 120       # km/h
SPEED_CRITICAL_THRESHOLD = 130      # km/h
RPM_WARNING_THRESHOLD = 7000        # rpm
RPM_CRITICAL_THRESHOLD = 8000       # rpm
FUEL_LOW_THRESHOLD = 100            # 0.1%単位 (= 10.0%)

# SRS-FUNC-024: アラート送信の最小間隔（秒）
ALERT_COOLDOWN_SECONDS = 1.0


# ==============================================================================
# クライアント本体
# ==============================================================================

class VehicleStatusClient:
    """車両ステータス SOME/IP クライアント"""

    def __init__(self, host: str, port: int, server_host: str, server_port: int):
        self.host = host
        self.port = port
        self.server_host = server_host
        self.server_port = server_port
        self.running = False
        self.sock: socket.socket | None = None
        self.session_id = 0
        self.client_id = 0x0100  # クライアント固有ID

        # アラートのクールダウン管理用
        # キー: AlertType, 値: 最後に送信した時刻
        self.last_alert_time: dict[int, float] = {}

        # 統計情報
        self.stats = {
            "notifications_received": 0,
            "validation_errors": 0,
            "alerts_sent": 0,
        }

    def _next_session_id(self) -> int:
        """セッションIDをインクリメントして返す"""
        self.session_id = (self.session_id + 1) & 0xFFFF
        if self.session_id == 0:
            self.session_id = 1
        return self.session_id

    # ==========================================================================
    # 起動・終了
    # ==========================================================================

    async def start(self):
        """クライアントを起動"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

        self.running = True
        # SRS-NFR-005: 起動時に接続情報を表示
        logger.info(f"=== 車両ステータスクライアント起動 ===")
        logger.info(f"  バインド     : {self.host}:{self.port}")
        logger.info(f"  サーバ       : {self.server_host}:{self.server_port}")
        logger.info(f"=====================================")

        await self._receive_loop()

    def stop(self):
        """クライアントを停止"""
        self.running = False
        logger.info(f"クライアント停止 (受信: {self.stats['notifications_received']}, "
                     f"バリデーションエラー: {self.stats['validation_errors']}, "
                     f"アラート送信: {self.stats['alerts_sent']})")
        if self.sock:
            self.sock.close()

    # ==========================================================================
    # Notification 受信処理
    # ==========================================================================

    async def _receive_loop(self):
        """メインの受信ループ"""
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                data, addr = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.sock.recvfrom(4096)),
                    timeout=0.5,
                )
                self._handle_received_message(data, addr)
            except (asyncio.TimeoutError, BlockingIOError):
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"受信エラー: {e}")

    def _handle_received_message(self, data: bytes, addr: tuple[str, int]):
        """
        受信メッセージを処理する

        TODO: 以下を実装してください
          1. SOME/IPヘッダーをデシリアライズする (SRS-FUNC-002)
          2. Service ID が VEHICLE_STATUS_SERVICE_ID であることを検証する
          3. Message Type に応じて処理を振り分ける:
             - NOTIFICATION (0x02) → _handle_notification()
             - RESPONSE (0x80)    → _handle_response()
             - ERROR (0x81)       → _handle_error()
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    def _handle_notification(self, header: SomeIpHeader, payload: bytes):
        """
        Notification メッセージの処理

        TODO: 以下を実装してください
          1. Method ID が NOTIFY_VEHICLE_STATUS (0x8001) であることを確認 (SRS-FUNC-002)
          2. ペイロードを VehicleStatus にデシリアライズする (SRS-FUNC-003)
          3. バリデーションを実行する (SRS-FUNC-030, 031, 032)
          4. コンソールに表示する (SRS-FUNC-004)
          5. アラート判定を行う (SRS-FUNC-020〜024)
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    # ==========================================================================
    # バリデーション
    # ==========================================================================

    def _validate_vehicle_status(self, status: VehicleStatus) -> bool:
        """
        受信データのバリデーション

        TODO: 以下を実装してください (SRS-FUNC-030, 031)
          - VehicleStatus.validate() を呼び出してエラーリストを取得
          - エラーがあれば警告ログを出力し False を返す
          - エラーがなければ True を返す

        Returns:
            True: バリデーション通過, False: バリデーション失敗
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    # ==========================================================================
    # アラート判定・送信
    # ==========================================================================

    def _check_and_send_alerts(self, status: VehicleStatus):
        """
        閾値チェックとアラート送信

        TODO: 以下を実装してください
          - 車速チェック (SRS-FUNC-020, 023)
            - 120 km/h超過 → SPEED_WARNING (severity: WARNING)
            - 130 km/h超過 → SPEED_WARNING (severity: CRITICAL)
          - 回転数チェック (SRS-FUNC-021, 023)
            - 7000 rpm超過 → RPM_WARNING (severity: WARNING)
            - 8000 rpm超過 → RPM_WARNING (severity: CRITICAL)
          - 燃料チェック (SRS-FUNC-022)
            - 10.0%未満 → FUEL_LOW_WARNING (severity: WARNING)
          - クールダウンチェック (SRS-FUNC-024)
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    def _can_send_alert(self, alert_type: int) -> bool:
        """
        アラートのクールダウンチェック (SRS-FUNC-024)

        TODO: 以下を実装してください
          - last_alert_time に記録された前回送信時刻を確認
          - ALERT_COOLDOWN_SECONDS 以上経過していれば True
          - そうでなければ False
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    def _send_alert(self, alert_type: int, severity: int,
                    trigger_value: int, threshold: int):
        """
        アラートメッセージを送信する

        TODO: 以下を実装してください
          1. AlertMessage を作成しシリアライズ
          2. SOME/IPヘッダーを作成 (Service ID, Method ID=0x0003, Message Type=REQUEST)
          3. サーバに送信
          4. last_alert_time を更新
          5. ログ出力
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    # ==========================================================================
    # Request/Response
    # ==========================================================================

    def send_get_vehicle_status(self) -> VehicleStatus | None:
        """
        GET_VEHICLE_STATUS リクエストを送信し、レスポンスを受信する (SRS-FUNC-010)

        TODO: 以下を実装してください
          1. SOME/IPヘッダーを作成 (Method ID=0x0001, Message Type=REQUEST)
          2. サーバに送信
          3. レスポンスを受信 (タイムアウト: 3秒) (SRS-FUNC-012)
          4. レスポンスのReturn Codeを検証 (SRS-FUNC-013)
          5. VehicleStatusをデシリアライズして返す

        Returns:
            VehicleStatus or None (タイムアウト/エラー時)
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    def send_get_diagnostic_info(self) -> DiagnosticInfo | None:
        """
        GET_DIAGNOSTIC_INFO リクエストを送信し、レスポンスを受信する (SRS-FUNC-011)

        TODO: 以下を実装してください
          send_get_vehicle_status() と同様のパターンで実装
          Method ID は 0x0002 を使用

        Returns:
            DiagnosticInfo or None (タイムアウト/エラー時)
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---

    # ==========================================================================
    # レスポンス処理
    # ==========================================================================

    def _handle_response(self, header: SomeIpHeader, payload: bytes):
        """レスポンスメッセージの処理（Request/Response用）"""
        logger.info(f"[RES] Method=0x{header.method_id:04X}, "
                     f"Return={header.return_code}, "
                     f"Payload={len(payload)} bytes")

    def _handle_error(self, header: SomeIpHeader, payload: bytes):
        """
        エラーレスポンスの処理 (SRS-FUNC-013)

        TODO: 以下を実装してください
          - Return Codeに応じたエラーログを出力
        """
        # --- ここから実装 ---

        pass  # この行を削除して実装してください

        # --- ここまで ---


# ==============================================================================
# エントリポイント
# ==============================================================================

def main():
    # 引数の処理
    parser = argparse.ArgumentParser(description="車両ステータス SOME/IP クライアント")
    parser.add_argument("--host", default="127.0.0.1", help="バインドアドレス (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=30491, help="クライアントポート (default: 30491)")
    parser.add_argument("--server-host", default="127.0.0.1", help="サーバアドレス (default: 127.0.0.1)")
    parser.add_argument("--server-port", type=int, default=30490, help="サーバポート (default: 30490)")
    args = parser.parse_args()

    # クライアント初期化
    client = VehicleStatusClient(args.host, args.port, args.server_host, args.server_port)

    # イベントループとして初期化
    loop = asyncio.new_event_loop()

    # シャットダウン時の処理
    def shutdown(sig, frame):
        client.stop()
        loop.stop()

    # 特定のシグナルを受け取ったらシャットダウン処理をするための処理
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        # 完了するまで終わらないようにスタートさせる
        loop.run_until_complete(client.start())
    except KeyboardInterrupt:
        # キーボードから強制終了した場合の処理
        pass
    finally:
        # 終了時に後処理をする
        client.stop()
        loop.close()
        logger.info("クライアント終了")


if __name__ == "__main__":
    main()
