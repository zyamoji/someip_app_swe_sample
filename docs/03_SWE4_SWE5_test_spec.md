# テスト仕様書
## 車両ステータス通知クライアント

| 項目 | 内容 |
|------|------|
| 文書ID | TS-VSCL-001 |
| 版数 | 1.0 |
| 作成日 |  |
| テスト担当 |  |
| A-SPICEプロセス | SWE.4 ソフトウェアユニット検証 / SWE.5 ソフトウェア結合テスト |

---

## 1. テスト方針

### 1.1 テスト対象
車両ステータス通知クライアントの全機能要件（SRS-VSCL-001）

### 1.2 テストレベル

| レベル | 対象 | ツール |
|--------|------|--------|
| ユニットテスト (SWE.4) | デシリアライズ、バリデーション、アラート判定ロジック | pytest |
| 結合テスト (SWE.5) | サーバとの実通信 | pytest + サンプルサーバ |

### 1.3 合格基準
- 全「必須」要件に対するテストケースが PASS であること
- テストカバレッジ: 要件カバレッジ 100%（全必須要件にテスト紐付け）

---

## 2. ユニットテスト仕様 (SWE.4)

### 2.1 デシリアライズテスト

| TC-ID | 対応要件 | テスト内容 | 入力 | 期待結果 | 結果 |
|-------|---------|-----------|------|---------|------|
| UT-001 | SRS-FUNC-003 | 正常なVehicleStatusペイロード(12bytes)をデシリアライズできること | `00 3C 07 D0 03 00 00 01 E2 40 03 20` | speed=60, rpm=2000, gear=3, signal=0, odo=123456, fuel=800 | |
| UT-002 | SRS-FUNC-032 | ペイロードが12bytes未満の場合にエラーとなること | 11bytesのデータ | ValueError発生 | |
| UT-003 | SRS-FUNC-032 | ペイロードが0bytesの場合にエラーとなること | 空のbytes | ValueError発生 | |
| UT-004 | SRS-FUNC-002 | SOME/IPヘッダーのService IDを正しく解析できること | Service ID=0x1001のヘッダー | service_id == 0x1001 | |
| UT-005 | SRS-FUNC-002 | SOME/IPヘッダーのMethod IDを正しく解析できること | Method ID=0x8001のヘッダー | method_id == 0x8001 | |

### 2.2 バリデーションテスト

| TC-ID | 対応要件 | テスト内容 | 入力 | 期待結果 | 結果 |
|-------|---------|-----------|------|---------|------|
| UT-010 | SRS-FUNC-030 | 全フィールドが正常範囲内のデータがバリデーションを通過すること | speed=60, rpm=2000, gear=3 | エラーなし | |
| UT-011 | SRS-FUNC-030 | speed=301 (範囲外) を検出できること | speed=301 | speed範囲外エラー | |
| UT-012 | SRS-FUNC-030 | rpm=10001 (範囲外) を検出できること | rpm=10001 | rpm範囲外エラー | |
| UT-013 | SRS-FUNC-030 | gear_position=11 (範囲外) を検出できること | gear=11 | gear範囲外エラー | |
| UT-014 | SRS-FUNC-030 | 境界値テスト: speed=0 (最小値) が正常であること | speed=0 | エラーなし | |
| UT-015 | SRS-FUNC-030 | 境界値テスト: speed=300 (最大値) が正常であること | speed=300 | エラーなし | |
| UT-016 | SRS-FUNC-030 | （参加者が追加: fuel_levelの境界値テスト） | | | |

### 2.3 アラート判定テスト

| TC-ID | 対応要件 | テスト内容 | 入力 | 期待結果 | 結果 |
|-------|---------|-----------|------|---------|------|
| UT-020 | SRS-FUNC-020 | speed=121でSPEED_WARNINGアラートが生成されること | speed=121 | alert_type=0x01, severity=2 | |
| UT-021 | SRS-FUNC-020 | speed=120ではアラートが生成されないこと | speed=120 | アラートなし | |
| UT-022 | SRS-FUNC-023 | speed=131でseverity=CRITICAL(3)となること | speed=131 | severity=3 | |
| UT-023 | SRS-FUNC-021 | rpm=7001でRPM_WARNINGアラートが生成されること | rpm=7001 | alert_type=0x02 | |
| UT-024 | SRS-FUNC-022 | fuel_level=99 (9.9%) でFUEL_LOW_WARNINGが生成されること | fuel=99 | alert_type=0x03 | |
| UT-025 | SRS-FUNC-022 | fuel_level=100 (10.0%) ではアラートが生成されないこと | fuel=100 | アラートなし | |
| UT-026 | SRS-FUNC-023 | （参加者が追加: RPM 8001でCRITICALとなるテスト） | | | |

---

## 3. 結合テスト仕様 (SWE.5)

**前提条件:** サンプルサーバ (`vehicle_status_server.py`) を `--scenario test` で起動済みであること。

### 3.1 Notification受信テスト

| TC-ID | 対応要件 | テスト内容 | 手順 | 期待結果 | 結果 |
|-------|---------|-----------|------|---------|------|
| IT-001 | SRS-FUNC-001 | クライアントがNotificationを受信できること | 1. サーバ起動 2. クライアント起動 3. 5秒間受信 | 1件以上の受信成功 | |
| IT-002 | SRS-FUNC-004 | 受信データがコンソールに表示されること | IT-001と同一 | 車速等6項目が表示される | |
| IT-003 | SRS-NFR-003 | 10秒間で100ms周期のNotificationを概ね取りこぼさないこと | 1. 10秒間受信 2. 受信件数カウント | 受信数 ≥ 90件 (90%以上) | |

### 3.2 Request/Responseテスト

| TC-ID | 対応要件 | テスト内容 | 手順 | 期待結果 | 結果 |
|-------|---------|-----------|------|---------|------|
| IT-010 | SRS-FUNC-010 | GET_VEHICLE_STATUSのリクエスト/レスポンスが成功すること | 1. リクエスト送信 2. レスポンス受信 | Return Code = E_OK, VehicleStatusデータ取得 | |
| IT-011 | SRS-FUNC-011 | GET_DIAGNOSTIC_INFOのリクエスト/レスポンスが成功すること | 1. リクエスト送信 2. レスポンス受信 | Return Code = E_OK, DiagnosticInfoデータ取得 | |
| IT-012 | SRS-FUNC-013 | 不正なMethod IDに対してエラーレスポンスを受信できること | Method ID=0x9999でリクエスト | Message Type=ERROR, Return Code=E_UNKNOWN_METHOD | |
| IT-013 | SRS-FUNC-012 | （タイムアウトのテスト） | | | |

### 3.3 アラート送受信テスト

| TC-ID | 対応要件 | テスト内容 | 手順 | 期待結果 | 結果 |
|-------|---------|-----------|------|---------|------|
| IT-020 | SRS-FUNC-020 | 速度超過時にアラートが送信されACKが返ること | 1. --scenario testでサーバ起動 2. speed>120のデータ受信を待つ 3. アラート送信確認 | ALERTリクエスト送信、ACKレスポンス受信 | |
| IT-021 | SRS-FUNC-022 | （参加者が追加: 燃料低下アラートのテスト） | | | |

---

## 4. トレーサビリティマトリクス

以下の表を完成させ、全必須要件がテストでカバーされていることを確認すること。

| 要件ID | UT-テストID | IT-テストID | カバー状態 |
|--------|-----------|-----------|-----------|
| SRS-FUNC-001 | - | IT-001 | ○ |
| SRS-FUNC-002 | UT-004, UT-005 | - | ○ |
| SRS-FUNC-003 | UT-001 | - | ○ |
| SRS-FUNC-004 | - | IT-002 | ○ |
| SRS-FUNC-010 | - | IT-010 | ○ |
| SRS-FUNC-011 | - | IT-011 | ○ |
| SRS-FUNC-012 | - | 要追加 | △ |
| SRS-FUNC-013 | - | IT-012 | ○ |
| SRS-FUNC-020 | UT-020, UT-021 | IT-020 | ○ |
| SRS-FUNC-021 | UT-023 | 要追加 | △ |
| SRS-FUNC-022 | UT-024, UT-025 | 要追加 | △ |
| SRS-FUNC-023 | UT-022 | - | ○ |
| SRS-FUNC-024 | 要追加 | 要追加 | △ |
| SRS-FUNC-030 | UT-010〜016 | - | ○ |
| SRS-FUNC-031 | 要追加 | - | △ |
| SRS-FUNC-032 | UT-002, UT-003 | - | ○ |

**凡例:** ○=カバー済み △=追加する必要あり ×=未カバー

---

## 5. テスト実行方法

```bash
# ユニットテスト実行
pytest tests/test_unit.py -v

# 結合テスト実行 (事前にサーバを起動しておくこと)
# ターミナル1:
python server/vehicle_status_server.py --scenario test
# ターミナル2:
pytest tests/test_integration.py -v

# 全テスト実行 + カバレッジ
pytest tests/ -v --tb=short
```
