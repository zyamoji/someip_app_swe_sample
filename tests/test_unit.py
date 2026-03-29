"""
ユニットテスト (SWE.4)
======================
テスト仕様書 TS-VSCL-001 §2 に対応するユニットテスト。

【課題】
  TODO 箇所のテストケースを実装してください。
  テスト仕様書のトレーサビリティマトリクスで △ になっている項目も
  追加してください。

実行方法:
  pytest tests/test_unit.py -v
"""

import struct
import sys
from pathlib import Path

import pytest

# 共通モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
from someip_common import (
    SomeIpHeader, MessageType, ReturnCode,
    VEHICLE_STATUS_SERVICE_ID, VehicleStatusMethodId,
    VehicleStatus, DiagnosticInfo,
    AlertMessage, AlertType, ALERT_METHOD_ID,
    HEADER_SIZE,
)


# ==============================================================================
# TC: UT-001〜005 デシリアライズテスト
# ==============================================================================

class TestDeserialization:
    """SOME/IPヘッダーおよびペイロードのデシリアライズテスト"""

    def test_ut001_vehicle_status_normal(self):
        """UT-001: 正常なVehicleStatusペイロードをデシリアライズできること"""
        # 入力: speed=60, rpm=2000, gear=3, signal=0, odo=123456, fuel=800
        payload = struct.pack("!HHBBIH", 60, 2000, 3, 0, 123456, 800)

        status = VehicleStatus.deserialize(payload)

        assert status.vehicle_speed == 60
        assert status.engine_rpm == 2000
        assert status.gear_position == 3
        assert status.turn_signal == 0
        assert status.odometer == 123456
        assert status.fuel_level == 800

    def test_ut002_payload_too_short(self):
        """UT-002: ペイロードが12bytes未満の場合にValueErrorとなること"""
        short_payload = b"\x00" * 11  # 11 bytes (不足)

        with pytest.raises(ValueError):
            VehicleStatus.deserialize(short_payload)

    def test_ut003_payload_empty(self):
        """UT-003: ペイロードが0bytesの場合にValueErrorとなること"""
        with pytest.raises(ValueError):
            VehicleStatus.deserialize(b"")

    def test_ut004_header_service_id(self):
        """UT-004: SOME/IPヘッダーのService IDを正しく解析できること"""
        header = SomeIpHeader(
            service_id=VEHICLE_STATUS_SERVICE_ID,
            method_id=VehicleStatusMethodId.NOTIFY_VEHICLE_STATUS,
            message_type=MessageType.NOTIFICATION,
        )
        raw = header.serialize()
        parsed, _ = SomeIpHeader.deserialize(raw)

        assert parsed.service_id == VEHICLE_STATUS_SERVICE_ID

    def test_ut005_header_method_id(self):
        """UT-005: SOME/IPヘッダーのMethod IDを正しく解析できること"""
        header = SomeIpHeader(
            service_id=VEHICLE_STATUS_SERVICE_ID,
            method_id=VehicleStatusMethodId.NOTIFY_VEHICLE_STATUS,
            message_type=MessageType.NOTIFICATION,
        )
        raw = header.serialize()
        parsed, _ = SomeIpHeader.deserialize(raw)

        assert parsed.method_id == VehicleStatusMethodId.NOTIFY_VEHICLE_STATUS


# ==============================================================================
# TC: UT-010〜016 バリデーションテスト
# ==============================================================================

class TestValidation:
    """データバリデーションのテスト"""

    def test_ut010_all_fields_valid(self):
        """UT-010: 全フィールドが正常範囲内のデータがバリデーションを通過すること"""
        status = VehicleStatus(
            vehicle_speed=60, engine_rpm=2000, gear_position=3,
            turn_signal=0, odometer=50000, fuel_level=500
        )
        errors = status.validate()
        assert len(errors) == 0

    def test_ut011_speed_over_range(self):
        """UT-011: speed=301 (範囲外) を検出できること"""
        status = VehicleStatus(vehicle_speed=301)
        errors = status.validate()
        assert any("vehicle_speed" in e for e in errors)

    def test_ut012_rpm_over_range(self):
        """UT-012: rpm=10001 (範囲外) を検出できること"""
        status = VehicleStatus(engine_rpm=10001)
        errors = status.validate()
        assert any("engine_rpm" in e for e in errors)

    def test_ut013_gear_over_range(self):
        """UT-013: gear_position=11 (範囲外) を検出できること"""
        status = VehicleStatus(gear_position=11)
        errors = status.validate()
        assert any("gear_position" in e for e in errors)

    def test_ut014_speed_min_boundary(self):
        """UT-014: 境界値テスト - speed=0 (最小値) が正常であること"""
        status = VehicleStatus(vehicle_speed=0)
        errors = status.validate()
        assert not any("vehicle_speed" in e for e in errors)

    def test_ut015_speed_max_boundary(self):
        """UT-015: 境界値テスト - speed=300 (最大値) が正常であること"""
        status = VehicleStatus(vehicle_speed=300)
        errors = status.validate()
        assert not any("vehicle_speed" in e for e in errors)

    def test_ut016_fuel_level_boundary(self):
        """
        UT-016: 境界値テスト - fuel_levelの境界値

        TODO: 以下を実装してください
          - fuel_level=0 (最小値) が正常であること
          - fuel_level=1000 (最大値) が正常であること
          - fuel_level=1001 (範囲外) がエラーとなること
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---


# ==============================================================================
# TC: UT-020〜026 アラート判定テスト
# ==============================================================================

class TestAlertJudgment:
    """
    アラート判定ロジックのテスト

    注意: これらのテストは、参加者が vehicle_status_client.py に
    実装したアラート判定ロジックをテストします。
    クライアントの実装方法に応じて、テスト方法を調整してください。

    ここでは、判定ロジックを独立した関数として抽出することを推奨します。
    """

    # --- アラート判定ロジックのヘルパー ---
    # クライアント実装時に、アラート判定を独立関数として抽出すると
    # テストしやすくなります。以下はその判定ロジックの仕様です。

    @staticmethod
    def judge_speed_alert(speed: int) -> tuple[bool, int] | None:
        """
        速度アラート判定 (参考実装)

        TODO: 参加者は自身のクライアント実装に合わせてこのロジックを
              書き換えるか、クライアントのメソッドを直接テストしてください。

        Returns:
            (should_alert, severity) or None
        """
        if speed > 130:
            return (True, 3)  # CRITICAL
        elif speed > 120:
            return (True, 2)  # WARNING
        return None

    def test_ut020_speed_121_triggers_warning(self):
        """UT-020: speed=121でSPEED_WARNINGアラートが生成されること"""
        result = self.judge_speed_alert(121)
        assert result is not None
        assert result[0] is True   # アラートあり
        assert result[1] == 2      # WARNING

    def test_ut021_speed_120_no_alert(self):
        """UT-021: speed=120ではアラートが生成されないこと"""
        result = self.judge_speed_alert(120)
        assert result is None

    def test_ut022_speed_131_critical(self):
        """UT-022: speed=131でseverity=CRITICAL(3)となること"""
        result = self.judge_speed_alert(131)
        assert result is not None
        assert result[1] == 3  # CRITICAL

    def test_ut023_rpm_7001_triggers_warning(self):
        """
        UT-023: rpm=7001でRPM_WARNINGアラートが生成されること

        TODO: 参加者が実装してください
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---

    def test_ut024_fuel_99_triggers_warning(self):
        """
        UT-024: fuel_level=99 (9.9%) でFUEL_LOW_WARNINGが生成されること

        TODO: 参加者が実装してください
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---

    def test_ut025_fuel_100_no_alert(self):
        """
        UT-025: fuel_level=100 (10.0%) ではアラートが生成されないこと

        TODO: 参加者が実装してください
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---

    def test_ut026_rpm_8001_critical(self):
        """
        UT-026: rpm=8001でCRITICALとなること

        TODO: 参加者が実装してください
        """
        # --- ここから実装 ---
        pytest.skip("TODO: 参加者が実装")
        # --- ここまで ---


# ==============================================================================
# 追加テスト: シリアライズ往復テスト (参考)
# ==============================================================================

class TestRoundTrip:
    """シリアライズ → デシリアライズの往復テスト (参考実装)"""

    def test_vehicle_status_roundtrip(self):
        """VehicleStatusのシリアライズ→デシリアライズで値が保持されること"""
        original = VehicleStatus(
            vehicle_speed=100, engine_rpm=3500, gear_position=3,
            turn_signal=1, odometer=88888, fuel_level=650
        )
        serialized = original.serialize()
        restored = VehicleStatus.deserialize(serialized)

        assert restored.vehicle_speed == original.vehicle_speed
        assert restored.engine_rpm == original.engine_rpm
        assert restored.gear_position == original.gear_position
        assert restored.turn_signal == original.turn_signal
        assert restored.odometer == original.odometer
        assert restored.fuel_level == original.fuel_level

    def test_someip_header_roundtrip(self):
        """SOME/IPヘッダーのシリアライズ→デシリアライズで値が保持されること"""
        original = SomeIpHeader(
            service_id=0x1001, method_id=0x8001,
            client_id=0x0100, session_id=42,
            message_type=MessageType.NOTIFICATION,
            return_code=ReturnCode.E_OK,
        )
        payload = b"\x01\x02\x03\x04"
        raw = original.serialize(payload)
        restored, restored_payload = SomeIpHeader.deserialize(raw)

        assert restored.service_id == original.service_id
        assert restored.method_id == original.method_id
        assert restored.client_id == original.client_id
        assert restored.session_id == original.session_id
        assert restored.message_type == original.message_type
        assert restored.return_code == original.return_code
        assert restored_payload == payload

    def test_alert_message_roundtrip(self):
        """AlertMessageのシリアライズ→デシリアライズで値が保持されること"""
        original = AlertMessage(
            alert_type=AlertType.SPEED_WARNING,
            severity=3,
            trigger_value=135,
            threshold=120,
        )
        serialized = original.serialize()
        restored = AlertMessage.deserialize(serialized)

        assert restored.alert_type == original.alert_type
        assert restored.severity == original.severity
        assert restored.trigger_value == original.trigger_value
        assert restored.threshold == original.threshold
