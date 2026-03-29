# インターフェース仕様書 (IFS)
## 車両ステータス通知サービス SOME/IP インターフェース

| 項目 | 内容 |
|------|------|
| 文書ID | IFS-VS-001 |
| 版数 | 1.0 |
| 作成日 | 2026-03-28 |
| A-SPICEプロセス | SWE.2 ソフトウェアアーキテクチャ設計 / SWE.3 ソフトウェア詳細設計 |

---

## 1. サービス概要

### 1.1 サービス識別

| 項目 | 値 | 説明 |
|------|----|------|
| Service ID | 0x1001 | 車両ステータス通知サービス |
| Instance ID | 0x0001 | デフォルトインスタンス |
| Major Version | 1 | メジャーバージョン |
| Minor Version | 0 | マイナーバージョン |

### 1.2 通信構成

```
┌──────────────┐       UDP / SOME/IP        ┌──────────────┐
│              │  ◄──── Notification ─────  │              │
│   Client     │  ───── Request ─────────►  │   Server     │
│  (port:30491)│  ◄──── Response ────────  │  (port:30490)│
│              │  ───── Alert ───────────►  │              │
└──────────────┘                            └──────────────┘
```

### 1.3 メソッド一覧

| Method ID | メソッド名 | パターン | 方向 |
|-----------|-----------|----------|------|
| 0x8001 | NOTIFY_VEHICLE_STATUS | Notification | Server → Client |
| 0x0001 | GET_VEHICLE_STATUS | Request/Response | Client → Server → Client |
| 0x0002 | GET_DIAGNOSTIC_INFO | Request/Response | Client → Server → Client |
| 0x0003 | ALERT | Request/Response | Client → Server → Client |

---

## 2. データ定義

### 2.1 SOME/IP ヘッダー構造 (16 bytes)

全メッセージ共通。バイトオーダーは **Big Endian (Network Byte Order)**。

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Service ID            |          Method ID            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Length                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Client ID             |         Session ID            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Protocol Ver  | Interface Ver | Message Type  | Return Code   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| オフセット | サイズ | フィールド | 型 | 説明 |
|-----------|--------|-----------|-----|------|
| 0 | 2 | Service ID | uint16 | サービス識別子 |
| 2 | 2 | Method ID | uint16 | メソッド識別子 |
| 4 | 4 | Length | uint32 | Request ID以降のバイト長 (= 8 + ペイロード長) |
| 8 | 2 | Client ID | uint16 | クライアント識別子 |
| 10 | 2 | Session ID | uint16 | セッション識別子 (1〜65535, 0は無効) |
| 12 | 1 | Protocol Version | uint8 | 固定値: 0x01 |
| 13 | 1 | Interface Version | uint8 | 固定値: 0x01 |
| 14 | 1 | Message Type | uint8 | 下表参照 |
| 15 | 1 | Return Code | uint8 | 下表参照 |

#### Message Type 値

| 値 | 名称 | 用途 |
|----|------|------|
| 0x00 | REQUEST | クライアントからのリクエスト |
| 0x01 | REQUEST_NO_RETURN | 応答不要のリクエスト |
| 0x02 | NOTIFICATION | サーバからの通知 |
| 0x80 | RESPONSE | リクエストへの応答 |
| 0x81 | ERROR | エラー応答 |

#### Return Code 値

| 値 | 名称 | 説明 |
|----|------|------|
| 0x00 | E_OK | 正常 |
| 0x01 | E_NOT_OK | 汎用エラー |
| 0x02 | E_UNKNOWN_SERVICE | 未知のService ID |
| 0x03 | E_UNKNOWN_METHOD | 未知のMethod ID |
| 0x04 | E_NOT_READY | サービス準備未完了 |
| 0x06 | E_TIMEOUT | タイムアウト |
| 0x09 | E_MALFORMED_MESSAGE | メッセージ形式不正 |

### 2.2 ペイロード定義

#### 2.2.1 VehicleStatus (12 bytes)

NOTIFY_VEHICLE_STATUS および GET_VEHICLE_STATUS レスポンスで使用。

| オフセット | サイズ | フィールド | 型 | 単位 | 有効範囲 | 説明 |
|-----------|--------|-----------|-----|------|---------|------|
| 0 | 2 | vehicle_speed | uint16 | km/h | 0〜300 | 車速 |
| 2 | 2 | engine_rpm | uint16 | rpm | 0〜10000 | エンジン回転数 |
| 4 | 1 | gear_position | uint8 | - | 0〜10 | ギアポジション (下表参照) |
| 5 | 1 | turn_signal | uint8 | - | 0〜3 | ウィンカー状態 (下表参照) |
| 6 | 4 | odometer | uint32 | km | 0〜999999 | 走行距離 |
| 10 | 2 | fuel_level | uint16 | 0.1% | 0〜1000 | 燃料残量 (0=0.0%, 1000=100.0%) |

**gear_position 値:**

| 値 | 意味 |
|----|------|
| 0 | P (パーキング) |
| 1 | R (リバース) |
| 2 | N (ニュートラル) |
| 3 | D (ドライブ) |
| 4〜10 | M1〜M7 (マニュアルモード) |

**turn_signal 値:**

| 値 | 意味 |
|----|------|
| 0 | OFF |
| 1 | LEFT (左) |
| 2 | RIGHT (右) |
| 3 | HAZARD (ハザード) |

#### 2.2.2 DiagnosticInfo (8 bytes)

GET_DIAGNOSTIC_INFO レスポンスで使用。

| オフセット | サイズ | フィールド | 型 | 単位 | 有効範囲 | 説明 |
|-----------|--------|-----------|-----|------|---------|------|
| 0 | 4 | dtc_count | uint32 | - | 0〜65535 | DTC数 |
| 4 | 1 | battery_voltage | uint8 | 0.1V | 0〜255 | バッテリー電圧 (例: 128 = 12.8V) |
| 5 | 1 | coolant_temp | uint8 | ℃ | 0〜255 | 冷却水温 (オフセット: -40, 値130 = 90℃) |
| 6 | 2 | engine_load | uint16 | 0.1% | 0〜1000 | エンジン負荷率 |

#### 2.2.3 AlertMessage (8 bytes)

ALERT リクエストで使用。

| オフセット | サイズ | フィールド | 型 | 有効範囲 | 説明 |
|-----------|--------|-----------|-----|---------|------|
| 0 | 1 | alert_type | uint8 | 1〜3 | アラート種別 (下表参照) |
| 1 | 1 | severity | uint8 | 1〜3 | 重要度 (下表参照) |
| 2 | 2 | trigger_value | uint16 | - | アラート発生時の実測値 |
| 4 | 2 | threshold | uint16 | - | 閾値 |
| 6 | 2 | reserved | uint16 | 0x0000 | 予約領域 |

**alert_type 値:**

| 値 | 名称 | 説明 |
|----|------|------|
| 0x01 | SPEED_WARNING | 速度超過 |
| 0x02 | RPM_WARNING | 回転数超過 |
| 0x03 | FUEL_LOW_WARNING | 燃料残量低下 |

**severity 値:**

| 値 | 名称 |
|----|------|
| 1 | INFO |
| 2 | WARNING |
| 3 | CRITICAL |

---

## 3. 通信シーケンス

### 3.1 Notification (周期通知)

```
  Client                          Server
    |                               |
    |   [SOME/IP Notification]      |
    |  ◄──── VehicleStatus ──────  |  (100ms周期)
    |                               |
    |   [SOME/IP Notification]      |
    |  ◄──── VehicleStatus ──────  |  (100ms周期)
    |                               |
```

ヘッダー設定:
- Service ID: 0x1001
- Method ID: 0x8001
- Message Type: 0x02 (NOTIFICATION)
- Client ID: 0x0000
- Return Code: 0x00 (E_OK)

### 3.2 Request/Response (GET_VEHICLE_STATUS)

```
  Client                          Server
    |                               |
    |   [SOME/IP Request]           |
    |  ───── GET_VEHICLE_STATUS ──►|
    |                               |
    |   [SOME/IP Response]          |
    |  ◄──── VehicleStatus ──────  |
    |                               |
```

リクエストヘッダー設定:
- Service ID: 0x1001
- Method ID: 0x0001
- Message Type: 0x00 (REQUEST)
- Client ID: 任意 (クライアント固有値)
- Session ID: リクエスト毎にインクリメント
- ペイロード: なし (0 bytes)

レスポンスヘッダー設定:
- Service ID: 0x1001
- Method ID: 0x0001
- Message Type: 0x80 (RESPONSE)
- Client ID: リクエストと同一値
- Session ID: リクエストと同一値
- Return Code: 0x00 (E_OK)
- ペイロード: VehicleStatus (12 bytes)

### 3.3 Alert (アラート通知)

```
  Client                          Server
    |                               |
    |   [SOME/IP Request]           |
    |  ───── AlertMessage ────────►|
    |                               |
    |   [SOME/IP Response]          |
    |  ◄──── ACK (empty) ────────  |
    |                               |
```

リクエストヘッダー設定:
- Service ID: 0x1001
- Method ID: 0x0003
- Message Type: 0x00 (REQUEST)
- ペイロード: AlertMessage (8 bytes)

レスポンスヘッダー設定 (ACK):
- Message Type: 0x80 (RESPONSE)
- Return Code: 0x00 (E_OK)
- ペイロード: なし (0 bytes)

### 3.4 エラー時シーケンス

```
  Client                          Server
    |                               |
    |   [不正なリクエスト]           |
    |  ───── (unknown method) ───►  |
    |                               |
    |   [SOME/IP Error]             |
    |  ◄──── Return Code ────────  |  (E_UNKNOWN_METHOD等)
    |                               |
```

---

## 4. 通信パラメータ

| パラメータ | 値 |
|-----------|-----|
| トランスポート | UDP |
| サーバアドレス | 127.0.0.1 |
| サーバポート | 30490 |
| クライアントポート | 30491 |
| Notification周期 | 100 ms |
| リクエストタイムアウト | 3000 ms |
| バイトオーダー | Big Endian |
