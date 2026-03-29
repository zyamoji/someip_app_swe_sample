"""
車両ステータス通知サーバ (SOME/IP)
====================================
演習用サンプルサーバアプリケーション

機能:
  1. 車両ステータスを100ms周期でUDP Notification送信
  2. GET_VEHICLE_STATUS (Request/Response) に応答
  3. GET_DIAGNOSTIC_INFO (Request/Response) に応答
  4. ALERT (クライアントからの通知) を受信・ログ出力

使い方:
  python vehicle_status_server.py [--host HOST] [--port PORT] [--scenario SCENARIO]

シナリオ:
  city    : 市街地走行 (低速〜中速、頻繁な停止)
  highway : 高速走行 (高速巡航)
  test    : テスト用 (境界値を含む固定パターン)
"""

import argparse
import asyncio
import json
import logging
import math
import random
import signal
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# --- 同一ディレクトリの共通モジュールをインポート ---
sys.path.insert(0, str(Path(__file__).parent))
from someip_common import (
    SomeIpHeader, MessageType, ReturnCode,
    VEHICLE_STATUS_SERVICE_ID, VehicleStatusMethodId,
    VehicleStatus, DiagnosticInfo, AlertMessage, ALERT_METHOD_ID,
)

# ==============================================================================
# ロガー設定
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VehicleServer")


# ==============================================================================
# 走行シナリオ生成
# ==============================================================================

class DrivingScenario:
    """走行データを生成するシナリオエンジン"""

    def __init__(self, scenario_name: str = "city"):
        self.scenario = scenario_name
        self.tick = 0
        self.odometer = 12345
        self.fuel_level = 800  # 80.0%

    def generate(self) -> VehicleStatus:
        """現在のtickに基づいて車両ステータスを生成"""
        self.tick += 1

        if self.scenario == "city":
            return self._city_scenario()
        elif self.scenario == "highway":
            return self._highway_scenario()
        elif self.scenario == "test":
            return self._test_scenario()
        else:
            return self._city_scenario()

    def _city_scenario(self) -> VehicleStatus:
        """市街地走行: 加減速を繰り返す"""
        cycle = self.tick % 200  # 20秒周期

        if cycle < 50:      # 加速フェーズ
            speed = int(cycle * 1.2)
            gear = 3  # D
        elif cycle < 100:   # 巡航フェーズ
            speed = 60 + int(5 * math.sin(self.tick * 0.1))
            gear = 3
        elif cycle < 130:   # 減速フェーズ
            speed = max(0, int(60 - (cycle - 100) * 2))
            gear = 3
        else:               # 停車フェーズ
            speed = 0
            gear = 2  # N

        rpm = max(800, speed * 30 + random.randint(-100, 100))
        turn_signal = 1 if (150 <= cycle <= 170) else 0  # 左折ウィンカー

        self.odometer += speed // 3600  # 概算
        self.fuel_level = max(0, self.fuel_level - 1) if self.tick % 50 == 0 else self.fuel_level

        return VehicleStatus(
            vehicle_speed=min(speed, 300),
            engine_rpm=min(rpm, 10000),
            gear_position=gear,
            turn_signal=turn_signal,
            odometer=min(self.odometer, 999999),
            fuel_level=max(0, self.fuel_level),
        )

    def _highway_scenario(self) -> VehicleStatus:
        """高速走行: 高速巡航 + 時折の速度超過"""
        base_speed = 100
        # 時折120km/hを超える (閾値テスト用)
        spike = 30 if (self.tick % 150 < 10) else 0
        speed = base_speed + int(10 * math.sin(self.tick * 0.05)) + spike
        rpm = speed * 25 + random.randint(-200, 200)

        self.odometer += speed // 3600
        self.fuel_level = max(0, self.fuel_level - 1) if self.tick % 30 == 0 else self.fuel_level

        return VehicleStatus(
            vehicle_speed=min(speed, 300),
            engine_rpm=min(max(rpm, 0), 10000),
            gear_position=3,  # D
            turn_signal=0,
            odometer=min(self.odometer, 999999),
            fuel_level=max(0, self.fuel_level),
        )

    def _test_scenario(self) -> VehicleStatus:
        """テスト用: 境界値を含む固定パターン (10秒周期で切り替え)"""
        patterns = [
            VehicleStatus(0, 800, 0, 0, 0, 1000),          # 停車・満タン
            VehicleStatus(60, 2000, 3, 0, 50000, 500),      # 通常走行
            VehicleStatus(120, 4000, 3, 0, 100000, 200),     # 速度閾値ちょうど
            VehicleStatus(121, 4100, 3, 0, 100001, 199),     # 速度閾値超過
            VehicleStatus(180, 6000, 3, 2, 200000, 100),     # 高速 + 右ウィンカー
            VehicleStatus(0, 800, 1, 3, 300000, 50),         # 停車・R・ハザード・燃料低
            VehicleStatus(300, 10000, 10, 0, 999999, 0),     # 最大値
            VehicleStatus(0, 0, 0, 0, 0, 0),                 # 最小値
        ]
        index = (self.tick // 100) % len(patterns)
        return patterns[index]


# ==============================================================================
# SOME/IP サーバ
# ==============================================================================

class VehicleStatusServer:
    """車両ステータス SOME/IP サーバ"""

    def __init__(self, host: str, port: int, client_port: int, scenario: str):
        self.host = host
        self.port = port
        self.client_port = client_port
        self.scenario = DrivingScenario(scenario)
        self.session_id = 0
        self.running = False
        self.sock: socket.socket | None = None
        self.subscribers: set[tuple[str, int]] = set()  # (host, port)
        self.stats = {"notifications_sent": 0, "requests_handled": 0, "alerts_received": 0}

    def _next_session_id(self) -> int:
        self.session_id = (self.session_id + 1) & 0xFFFF
        if self.session_id == 0:
            self.session_id = 1
        return self.session_id

    async def start(self):
        """サーバを起動"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

        self.running = True
        logger.info(f"=== 車両ステータスサーバ起動 ===")
        logger.info(f"  アドレス       : {self.host}:{self.port}")
        logger.info(f"  クライアントPort: {self.client_port}")
        logger.info(f"  シナリオ       : {self.scenario.scenario}")
        logger.info(f"  Service ID     : 0x{VEHICLE_STATUS_SERVICE_ID:04X}")
        logger.info(f"  通知周期       : 100ms")
        logger.info(f"================================")

        # 周期通知タスクとリクエスト受信タスクを並行実行
        await asyncio.gather(
            self._notification_loop(),
            self._receive_loop(),
        )

    async def _notification_loop(self):
        """100ms周期で車両ステータスをNotification送信"""
        loop = asyncio.get_event_loop()
        while self.running:
            status = self.scenario.generate()
            payload = status.serialize()

            header = SomeIpHeader(
                service_id=VEHICLE_STATUS_SERVICE_ID,
                method_id=VehicleStatusMethodId.NOTIFY_VEHICLE_STATUS,
                client_id=0x0000,
                session_id=self._next_session_id(),
                message_type=MessageType.NOTIFICATION,
                return_code=ReturnCode.E_OK,
            )

            message = header.serialize(payload)

            # 全登録クライアント、およびデフォルトのクライアントポートに送信
            targets = set(self.subscribers)
            targets.add((self.host, self.client_port))

            for target in targets:
                try:
                    self.sock.sendto(message, target)
                except OSError as e:
                    logger.warning(f"送信失敗 ({target}): {e}")

            self.stats["notifications_sent"] += 1

            if self.stats["notifications_sent"] % 100 == 0:
                logger.info(f"[周期通知] #{self.stats['notifications_sent']:>6d} | {status.to_display_string()}")

            await asyncio.sleep(0.1)

    async def _receive_loop(self):
        """クライアントからのRequest/Alertを受信"""
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                data, addr = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.sock.recvfrom(4096)),
                    timeout=0.5,
                )
                await self._handle_message(data, addr)
            except (asyncio.TimeoutError, BlockingIOError):
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"受信エラー: {e}")

    async def _handle_message(self, data: bytes, addr: tuple[str, int]):
        """受信メッセージの処理"""
        try:
            header, payload = SomeIpHeader.deserialize(data)
        except ValueError as e:
            logger.warning(f"不正なメッセージ ({addr}): {e}")
            return

        # サービスIDチェック
        if header.service_id != VEHICLE_STATUS_SERVICE_ID:
            logger.warning(f"未知のService ID: 0x{header.service_id:04X} ({addr})")
            self._send_error(header, ReturnCode.E_UNKNOWN_SERVICE, addr)
            return

        method_id = header.method_id

        if method_id == VehicleStatusMethodId.GET_VEHICLE_STATUS:
            self._handle_get_vehicle_status(header, addr)
        elif method_id == VehicleStatusMethodId.GET_DIAGNOSTIC_INFO:
            self._handle_get_diagnostic_info(header, addr)
        elif method_id == ALERT_METHOD_ID:
            self._handle_alert(header, payload, addr)
        else:
            logger.warning(f"未知のMethod ID: 0x{method_id:04X} ({addr})")
            self._send_error(header, ReturnCode.E_UNKNOWN_METHOD, addr)

    def _handle_get_vehicle_status(self, request_header: SomeIpHeader, addr: tuple[str, int]):
        """GET_VEHICLE_STATUS リクエストに応答"""
        self.stats["requests_handled"] += 1
        logger.info(f"[REQ] GET_VEHICLE_STATUS from {addr}")

        status = self.scenario.generate()
        response_header = SomeIpHeader(
            service_id=VEHICLE_STATUS_SERVICE_ID,
            method_id=VehicleStatusMethodId.GET_VEHICLE_STATUS,
            client_id=request_header.client_id,
            session_id=request_header.session_id,
            message_type=MessageType.RESPONSE,
            return_code=ReturnCode.E_OK,
        )
        self.sock.sendto(response_header.serialize(status.serialize()), addr)

    def _handle_get_diagnostic_info(self, request_header: SomeIpHeader, addr: tuple[str, int]):
        """GET_DIAGNOSTIC_INFO リクエストに応答"""
        self.stats["requests_handled"] += 1
        logger.info(f"[REQ] GET_DIAGNOSTIC_INFO from {addr}")

        diag = DiagnosticInfo(
            dtc_count=random.randint(0, 3),
            battery_voltage=128 + random.randint(-5, 5),  # 12.3-13.3V
            coolant_temp=130 + random.randint(-10, 10),    # 80-100℃
            engine_load=350 + random.randint(-50, 50),
        )
        response_header = SomeIpHeader(
            service_id=VEHICLE_STATUS_SERVICE_ID,
            method_id=VehicleStatusMethodId.GET_DIAGNOSTIC_INFO,
            client_id=request_header.client_id,
            session_id=request_header.session_id,
            message_type=MessageType.RESPONSE,
            return_code=ReturnCode.E_OK,
        )
        self.sock.sendto(response_header.serialize(diag.serialize()), addr)

    def _handle_alert(self, request_header: SomeIpHeader, payload: bytes, addr: tuple[str, int]):
        """クライアントからのアラートを受信"""
        self.stats["alerts_received"] += 1
        try:
            alert = AlertMessage.deserialize(payload)
            alert_names = {1: "SPEED_WARNING", 2: "RPM_WARNING", 3: "FUEL_LOW_WARNING"}
            severity_names = {1: "INFO", 2: "WARNING", 3: "CRITICAL"}
            logger.info(
                f"[ALERT] {alert_names.get(alert.alert_type, 'UNKNOWN')} | "
                f"severity={severity_names.get(alert.severity, '?')} | "
                f"value={alert.trigger_value} | threshold={alert.threshold} | from {addr}"
            )
        except ValueError as e:
            logger.warning(f"不正なAlertペイロード ({addr}): {e}")
            self._send_error(request_header, ReturnCode.E_MALFORMED_MESSAGE, addr)
            return

        # ACK応答
        response_header = SomeIpHeader(
            service_id=VEHICLE_STATUS_SERVICE_ID,
            method_id=ALERT_METHOD_ID,
            client_id=request_header.client_id,
            session_id=request_header.session_id,
            message_type=MessageType.RESPONSE,
            return_code=ReturnCode.E_OK,
        )
        self.sock.sendto(response_header.serialize(), addr)

    def _send_error(self, request_header: SomeIpHeader, return_code: ReturnCode, addr: tuple[str, int]):
        """エラーレスポンスを送信"""
        error_header = SomeIpHeader(
            service_id=request_header.service_id,
            method_id=request_header.method_id,
            client_id=request_header.client_id,
            session_id=request_header.session_id,
            message_type=MessageType.ERROR,
            return_code=return_code,
        )
        self.sock.sendto(error_header.serialize(), addr)

    def stop(self):
        """サーバを停止"""
        self.running = False
        logger.info(f"サーバ停止中... (通知: {self.stats['notifications_sent']}, "
                     f"リクエスト: {self.stats['requests_handled']}, "
                     f"アラート: {self.stats['alerts_received']})")
        if self.sock:
            self.sock.close()


# ==============================================================================
# エントリポイント
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="車両ステータス SOME/IP サーバ")
    parser.add_argument("--host", default="127.0.0.1", help="バインドアドレス (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=30490, help="サーバポート (default: 30490)")
    parser.add_argument("--client-port", type=int, default=30491, help="クライアント送信先ポート (default: 30491)")
    parser.add_argument("--scenario", choices=["city", "highway", "test"], default="city",
                        help="走行シナリオ (default: city)")
    args = parser.parse_args()

    server = VehicleStatusServer(args.host, args.port, args.client_port, args.scenario)

    loop = asyncio.new_event_loop()

    def shutdown(sig, frame):
        server.stop()
        loop.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(server.start())
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        loop.close()
        logger.info("サーバ終了")


if __name__ == "__main__":
    main()
