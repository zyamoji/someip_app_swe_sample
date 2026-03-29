"""
結合テスト (SWE.5)
==================
テスト仕様書 TS-VSCL-001 §3 に対応する結合テスト。

前提条件:
  サンプルサーバを --scenario test で起動しておくこと。
  $ python server/vehicle_status_server.py --scenario test

実行方法:
  pytest tests/test_integration.py -v

【課題】
  TODO 箇所のテストケースを実装してください。
"""

import socket
import struct
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
from someip_common import (
    SomeIpHeader, MessageType, ReturnCode,
    VEHICLE_STATUS_SERVICE_ID, VehicleStatusMethodId,
    VehicleStatus, DiagnosticInfo,
    AlertMessage, AlertType, ALERT_METHOD_ID,
    HEADER_SIZE,
)

# --- テスト設定 ---
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 30490
# 結合テスト用のクライアントポート (本番クライアントと競合しないよう別ポートを使用)
TEST_CLIENT_PORT = 30499
TIMEOUT = 3.0


# ==============================================================================
# フィクスチャ
# ==============================================================================

@pytest.fixture
def udp_socket():
    """テスト用UDPソケット"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((SERVER_HOST, TEST_CLIENT_PORT))
    sock.settimeout(TIMEOUT)
    yield sock
    sock.close()


def send_request(sock: socket.socket, method_id: int,
                 payload: bytes = b"", session_id: int = 1) -> tuple[SomeIpHeader, bytes]:
    """リクエスト送信 → レスポンス受信のヘルパー"""
    header = SomeIpHeader(
        service_id=VEHICLE_STATUS_SERVICE_ID,
        method_id=method_id,
        client_id=0x0200,  # テスト用クライアントID
        session_id=session_id,
        message_type=MessageType.REQUEST,
    )
    sock.sendto(header.serialize(payload), (SERVER_HOST, SERVER_PORT))
    data, _ = sock.recvfrom(4096)
    return SomeIpHeader.deserialize(data)


# ==============================================================================
# TC: IT-001〜003 Notification受信テスト
# ==============================================================================

class TestNotificationReceive:
    """Notification受信の結合テスト"""

    def test_it001_receive_notification(self, udp_socket):
        """IT-001: クライアントがNotificationを受信できること"""
        # サーバはデフォルトでクライアントポート30491に送信するため、
        # ここではGET_VEHICLE_STATUSリクエストでデータ取得を確認する。
        # (Notificationの受信テストは、クライアントアプリの実行で確認する)
        resp_header, resp_payload = send_request(
            udp_socket,
            VehicleStatusMethodId.GET_VEHICLE_STATUS
        )
        assert resp_header.message_type == MessageType.RESPONSE
        assert resp_header.return_code == ReturnCode.E_OK
        assert len(resp_payload) == VehicleStatus.PAYLOAD_SIZE

    def test_it003_notification_throughput(self, udp_socket):
        """
        IT-003: 10秒間で100ms周期のNotificationを概ね取りこぼさないこと

        注意: このテストはNotificationポート(30491)での受信が必要。
        簡易版として、10回連続リクエストの応答時間で性能を確認する。

        TODO: 参加者は本来のNotification受信テストに書き換えることを推奨
        """
        latencies = []
        for i in range(10):
            start = time.time()
            send_request(udp_socket, VehicleStatusMethodId.GET_VEHICLE_STATUS, session_id=i + 1)
            latency = time.time() - start
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 1.0, f"平均レイテンシが1秒を超過: {avg_latency:.3f}s"


# ==============================================================================
# TC: IT-010〜013 Request/Responseテスト
# ==============================================================================

class TestRequestResponse:
    """Request/Response の結合テスト"""

    def test_it010_get_vehicle_status(self, udp_socket):
        """IT-010: GET_VEHICLE_STATUSのリクエスト/レスポンスが成功すること"""
        resp_header, resp_payload = send_request(
            udp_socket,
            VehicleStatusMethodId.GET_VEHICLE_STATUS
        )

        # ヘッダー検証
        assert resp_header.service_id == VEHICLE_STATUS_SERVICE_ID
        assert resp_header.method_id == VehicleStatusMethodId.GET_VEHICLE_STATUS
        assert resp_header.message_type == MessageType.RESPONSE
        assert resp_header.return_code == ReturnCode.E_OK

        # ペイロード検証
        status = VehicleStatus.deserialize(resp_payload)
        assert 0 <= status.vehicle_speed <= 300
        assert 0 <= status.engine_rpm <= 10000

    def test_it011_get_diagnostic_info(self, udp_socket):
        """IT-011: GET_DIAGNOSTIC_INFOのリクエスト/レスポンスが成功すること"""
        resp_header, resp_payload = send_request(
            udp_socket,
            VehicleStatusMethodId.GET_DIAGNOSTIC_INFO
        )

        assert resp_header.message_type == MessageType.RESPONSE
        assert resp_header.return_code == ReturnCode.E_OK

        diag = DiagnosticInfo.deserialize(resp_payload)
        assert diag.battery_voltage > 0
        assert diag.coolant_temp > 0

    def test_it012_unknown_method_error(self, udp_socket):
        """IT-012: 不正なMethod IDに対してエラーレスポンスを受信できること"""
        resp_header, _ = send_request(
            udp_socket,
            0x9999  # 未定義のMethod ID
        )

        assert resp_header.message_type == MessageType.ERROR
        assert resp_header.return_code == ReturnCode.E_UNKNOWN_METHOD

    def test_it013_timeout(self):
        """
        IT-013: サーバ未起動時のタイムアウト

        TODO: 参加者が実装してください
          - 存在しないポート (例: 39999) にリクエストを送信
          - socket.timeout が発生することを確認
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---


# ==============================================================================
# TC: IT-020〜021 アラート送受信テスト
# ==============================================================================

class TestAlertExchange:
    """アラートの送受信テスト"""

    def test_it020_speed_alert_ack(self, udp_socket):
        """IT-020: 速度超過アラート送信に対しACKが返ること"""
        alert = AlertMessage(
            alert_type=AlertType.SPEED_WARNING,
            severity=2,
            trigger_value=125,
            threshold=120,
        )
        resp_header, resp_payload = send_request(
            udp_socket,
            ALERT_METHOD_ID,
            payload=alert.serialize(),
        )

        assert resp_header.message_type == MessageType.RESPONSE
        assert resp_header.return_code == ReturnCode.E_OK

    def test_it021_fuel_alert(self, udp_socket):
        """
        IT-021: 燃料低下アラートの送受信テスト

        TODO: 参加者が実装してください
          - FUEL_LOW_WARNING の AlertMessage を作成
          - サーバに送信し、ACKが返ることを確認
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---


# ==============================================================================
# 追加テスト (参加者向けチャレンジ)
# ==============================================================================

class TestAdditionalChallenges:
    """
    追加のテストケース (余裕がある参加者向け)

    以下のテストケースを実装してみてください:
    """

    def test_session_id_echo(self, udp_socket):
        """レスポンスのSession IDがリクエストと同一であること"""
        req_session = 12345
        resp_header, _ = send_request(
            udp_socket,
            VehicleStatusMethodId.GET_VEHICLE_STATUS,
            session_id=req_session,
        )
        assert resp_header.session_id == req_session

    def test_malformed_alert_payload(self, udp_socket):
        """
        不正なアラートペイロードに対するエラーハンドリング

        TODO: 参加者が実装してください
          - 7 bytes (不足) のペイロードをアラートとして送信
          - E_MALFORMED_MESSAGE が返ることを確認
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---
