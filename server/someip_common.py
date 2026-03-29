"""
SOME/IP プロトコル共通モジュール
================================
SOME/IP (Scalable service-Oriented MiddlewarE over IP) の
ヘッダー構造とシリアライズ/デシリアライズを提供する。

外部依存なし（Pure Python）で、プロトコルの構造を学習しやすくしている。

参考: AUTOSAR SOME/IP Protocol Specification (AUTOSAR_PRS_SOMEIPProtocol)
"""

import struct
import enum
from dataclasses import dataclass, field
from typing import Optional


# ==============================================================================
# SOME/IP 定数定義
# ==============================================================================

class MessageType(enum.IntEnum):
    """SOME/IP メッセージタイプ"""
    REQUEST = 0x00
    REQUEST_NO_RETURN = 0x01
    NOTIFICATION = 0x02
    RESPONSE = 0x80
    ERROR = 0x81


class ReturnCode(enum.IntEnum):
    """SOME/IP リターンコード"""
    E_OK = 0x00
    E_NOT_OK = 0x01
    E_UNKNOWN_SERVICE = 0x02
    E_UNKNOWN_METHOD = 0x03
    E_NOT_READY = 0x04
    E_NOT_REACHABLE = 0x05
    E_TIMEOUT = 0x06
    E_WRONG_PROTOCOL_VERSION = 0x07
    E_WRONG_INTERFACE_VERSION = 0x08
    E_MALFORMED_MESSAGE = 0x09
    E_WRONG_MESSAGE_TYPE = 0x0A


# プロトコルバージョン
PROTOCOL_VERSION = 0x01
INTERFACE_VERSION = 0x01

# SOME/IP-SD 関連定数
SD_SERVICE_ID = 0xFFFF
SD_METHOD_ID = 0x8100
SD_CLIENT_ID = 0x0000

# SOME/IP ヘッダーサイズ (16 bytes)
HEADER_SIZE = 16


# ==============================================================================
# SOME/IP ヘッダー
# ==============================================================================

@dataclass
class SomeIpHeader:
    """
    SOME/IP メッセージヘッダー (16 bytes)

    構造:
        [0:2]  Service ID          (uint16)
        [2:4]  Method ID           (uint16)
        [4:8]  Length              (uint32) - Request ID以降の長さ(8) + Payload長
        [8:10] Client ID           (uint16)
        [10:12] Session ID         (uint16)
        [12]   Protocol Version    (uint8)
        [13]   Interface Version   (uint8)
        [14]   Message Type        (uint8)
        [15]   Return Code         (uint8)
    """
    service_id: int
    method_id: int
    client_id: int = 0x0000
    session_id: int = 0x0001
    protocol_version: int = PROTOCOL_VERSION
    interface_version: int = INTERFACE_VERSION
    message_type: int = MessageType.REQUEST
    return_code: int = ReturnCode.E_OK

    def serialize(self, payload: bytes = b"") -> bytes:
        """ヘッダー + ペイロードをバイト列にシリアライズ"""
        length = 8 + len(payload)  # Request ID(4) + ProtVer(1) + IfVer(1) + MsgType(1) + RetCode(1) + Payload
        header = struct.pack(
            "!HHIHH4B",
            self.service_id,
            self.method_id,
            length,
            self.client_id,
            self.session_id,
            self.protocol_version,
            self.interface_version,
            self.message_type,
            self.return_code,
        )
        return header + payload

    @classmethod
    def deserialize(cls, data: bytes) -> tuple["SomeIpHeader", bytes]:
        """
        バイト列からヘッダーを復元し、ペイロードも返す。

        Returns:
            (SomeIpHeader, payload_bytes)

        Raises:
            ValueError: データが不正な場合
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(f"データ長不足: {len(data)} bytes (最低 {HEADER_SIZE} bytes 必要)")

        service_id, method_id, length, client_id, session_id, \
            proto_ver, if_ver, msg_type, ret_code = struct.unpack("!HHIHH4B", data[:HEADER_SIZE])

        payload_length = length - 8
        if payload_length < 0:
            raise ValueError(f"不正なLength値: {length}")

        payload = data[HEADER_SIZE:HEADER_SIZE + payload_length]

        header = cls(
            service_id=service_id,
            method_id=method_id,
            client_id=client_id,
            session_id=session_id,
            protocol_version=proto_ver,
            interface_version=if_ver,
            message_type=msg_type,
            return_code=ret_code,
        )
        return header, payload


# ==============================================================================
# 車両ステータスサービス固有の定義
# ==============================================================================

# サービスID / メソッドID / イベントグループID
VEHICLE_STATUS_SERVICE_ID = 0x1001
VEHICLE_STATUS_EVENT_GROUP_ID = 0x0001

class VehicleStatusMethodId(enum.IntEnum):
    """車両ステータスサービスのメソッドID"""
    # Event Notification (0x8000番台 = イベント)
    NOTIFY_VEHICLE_STATUS = 0x8001
    # Request/Response
    GET_VEHICLE_STATUS = 0x0001
    GET_DIAGNOSTIC_INFO = 0x0002


@dataclass
class VehicleStatus:
    """
    車両ステータスデータ

    ペイロード構造 (12 bytes, Big Endian):
        [0:2]   vehicle_speed   (uint16) - 車速 [km/h] (0-300)
        [2:4]   engine_rpm      (uint16) - エンジン回転数 [rpm] (0-10000)
        [4:5]   gear_position   (uint8)  - ギアポジション (0=P, 1=R, 2=N, 3=D, 4-10=M1-M7)
        [5:6]   turn_signal     (uint8)  - ウィンカー状態 (0=OFF, 1=LEFT, 2=RIGHT, 3=HAZARD)
        [6:10]  odometer        (uint32) - 走行距離 [km] (0-999999)
        [10:12] fuel_level      (uint16) - 燃料残量 [0.1%単位] (0-1000 = 0.0%-100.0%)
    """
    vehicle_speed: int = 0
    engine_rpm: int = 0
    gear_position: int = 0
    turn_signal: int = 0
    odometer: int = 0
    fuel_level: int = 500  # 50.0%

    # バリデーション用レンジ定義
    SPEED_RANGE = (0, 300)
    RPM_RANGE = (0, 10000)
    GEAR_RANGE = (0, 10)
    SIGNAL_RANGE = (0, 3)
    ODOMETER_RANGE = (0, 999999)
    FUEL_RANGE = (0, 1000)

    PAYLOAD_SIZE = 12

    def validate(self) -> list[str]:
        """データのバリデーション。エラーメッセージのリストを返す。"""
        errors = []
        if not (self.SPEED_RANGE[0] <= self.vehicle_speed <= self.SPEED_RANGE[1]):
            errors.append(f"vehicle_speed 範囲外: {self.vehicle_speed} (有効: {self.SPEED_RANGE})")
        if not (self.RPM_RANGE[0] <= self.engine_rpm <= self.RPM_RANGE[1]):
            errors.append(f"engine_rpm 範囲外: {self.engine_rpm} (有効: {self.RPM_RANGE})")
        if not (self.GEAR_RANGE[0] <= self.gear_position <= self.GEAR_RANGE[1]):
            errors.append(f"gear_position 範囲外: {self.gear_position} (有効: {self.GEAR_RANGE})")
        if not (self.SIGNAL_RANGE[0] <= self.turn_signal <= self.SIGNAL_RANGE[1]):
            errors.append(f"turn_signal 範囲外: {self.turn_signal} (有効: {self.SIGNAL_RANGE})")
        if not (self.ODOMETER_RANGE[0] <= self.odometer <= self.ODOMETER_RANGE[1]):
            errors.append(f"odometer 範囲外: {self.odometer} (有効: {self.ODOMETER_RANGE})")
        if not (self.FUEL_RANGE[0] <= self.fuel_level <= self.FUEL_RANGE[1]):
            errors.append(f"fuel_level 範囲外: {self.fuel_level} (有効: {self.FUEL_RANGE})")
        return errors

    def serialize(self) -> bytes:
        """ペイロードにシリアライズ (12 bytes, Big Endian)"""
        return struct.pack(
            "!HHBBIH",
            self.vehicle_speed,
            self.engine_rpm,
            self.gear_position,
            self.turn_signal,
            self.odometer,
            self.fuel_level,
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "VehicleStatus":
        """ペイロードからデシリアライズ"""
        if len(data) < cls.PAYLOAD_SIZE:
            raise ValueError(f"ペイロード長不足: {len(data)} bytes (最低 {cls.PAYLOAD_SIZE} bytes 必要)")

        speed, rpm, gear, signal, odo, fuel = struct.unpack("!HHBBIH", data[:cls.PAYLOAD_SIZE])
        return cls(
            vehicle_speed=speed,
            engine_rpm=rpm,
            gear_position=gear,
            turn_signal=signal,
            odometer=odo,
            fuel_level=fuel,
        )

    def to_display_string(self) -> str:
        """人が読める形式の文字列を返す"""
        gear_names = {0: "P", 1: "R", 2: "N", 3: "D"}
        gear_str = gear_names.get(self.gear_position, f"M{self.gear_position - 3}")
        signal_names = {0: "OFF", 1: "LEFT", 2: "RIGHT", 3: "HAZARD"}
        signal_str = signal_names.get(self.turn_signal, "UNKNOWN")

        return (
            f"速度: {self.vehicle_speed:>3d} km/h | "
            f"回転数: {self.engine_rpm:>5d} rpm | "
            f"ギア: {gear_str:>2s} | "
            f"ウィンカー: {signal_str:<6s} | "
            f"走行距離: {self.odometer:>6d} km | "
            f"燃料: {self.fuel_level / 10:.1f}%"
        )


@dataclass
class DiagnosticInfo:
    """
    診断情報データ (Request/Response用)

    ペイロード構造 (8 bytes, Big Endian):
        [0:4]   dtc_count       (uint32) - DTC数
        [4:5]   battery_voltage (uint8)  - バッテリー電圧 [0.1V単位] (0-255 = 0.0-25.5V)
        [5:6]   coolant_temp    (uint8)  - 冷却水温 [℃] (オフセット -40, 値0=−40℃, 値255=215℃)
        [6:8]   engine_load     (uint16) - エンジン負荷率 [0.1%単位] (0-1000)
    """
    dtc_count: int = 0
    battery_voltage: int = 128  # 12.8V
    coolant_temp: int = 130     # 90℃ (130 - 40)
    engine_load: int = 350      # 35.0%

    PAYLOAD_SIZE = 8

    def serialize(self) -> bytes:
        return struct.pack("!IBBH", self.dtc_count, self.battery_voltage,
                           self.coolant_temp, self.engine_load)

    @classmethod
    def deserialize(cls, data: bytes) -> "DiagnosticInfo":
        if len(data) < cls.PAYLOAD_SIZE:
            raise ValueError(f"ペイロード長不足: {len(data)} bytes (最低 {cls.PAYLOAD_SIZE} bytes 必要)")
        dtc, batt, coolant, load = struct.unpack("!IBBH", data[:cls.PAYLOAD_SIZE])
        return cls(dtc_count=dtc, battery_voltage=batt, coolant_temp=coolant, engine_load=load)


# ==============================================================================
# アラート定義 (クライアント → サーバへの応答)
# ==============================================================================

class AlertType(enum.IntEnum):
    """アラート種別"""
    SPEED_WARNING = 0x01       # 速度超過警告
    RPM_WARNING = 0x02         # 回転数超過警告
    FUEL_LOW_WARNING = 0x03    # 燃料残量低下警告


ALERT_METHOD_ID = 0x0003  # クライアント → サーバ (Request/Response)


@dataclass
class AlertMessage:
    """
    アラートメッセージ

    ペイロード構造 (8 bytes, Big Endian):
        [0:1]   alert_type      (uint8)  - アラート種別 (AlertType)
        [1:2]   severity        (uint8)  - 重要度 (1=INFO, 2=WARNING, 3=CRITICAL)
        [2:4]   trigger_value   (uint16) - アラート発生時の値
        [4:6]   threshold       (uint16) - 閾値
        [6:8]   reserved        (uint16) - 予約領域 (0x0000)
    """
    alert_type: int = AlertType.SPEED_WARNING
    severity: int = 2
    trigger_value: int = 0
    threshold: int = 0

    PAYLOAD_SIZE = 8

    def serialize(self) -> bytes:
        return struct.pack("!BBHHH", self.alert_type, self.severity,
                           self.trigger_value, self.threshold, 0x0000)

    @classmethod
    def deserialize(cls, data: bytes) -> "AlertMessage":
        if len(data) < cls.PAYLOAD_SIZE:
            raise ValueError(f"ペイロード長不足: {len(data)} bytes")
        atype, sev, tval, thresh, _ = struct.unpack("!BBHHH", data[:cls.PAYLOAD_SIZE])
        return cls(alert_type=atype, severity=sev, trigger_value=tval, threshold=thresh)
