# 演習ガイド
## SOME/IP通信アプリ開発演習

---

## 1. 演習の目的

この演習では、SOME/IPプロトコルを使った車両ステータス通知システムを題材に、以下のスキルを実践的に身につけます。

- **そもそも仕様書にどういう記載内容が必要で、どのようなデータがあれば良いのかを考える力**
- **仕様書を読み解き、実装を行うために情報を拾い切る力**
- **テスト仕様を設計し、自動テストを考えられる力**
- **AIを利用して、実装ができるようになる力**

## 2. 前提知識

- Python の基本文法（関数、クラス、例外処理）
- UDP通信の基本概念（送信先アドレス・ポート）
- バイナリデータの概念（バイトオーダー、structモジュール）

## 3. ファイル構成

```
exercise/
├── docs/
│   ├── 01_SWE1_software_requirements_spec.md   ← 要件仕様書 (必読)
│   ├── 02_SWE2_SWE3_interface_spec.md          ← インターフェース仕様書 (必読)
│   ├── 03_SWE4_SWE5_test_spec.md              ← テスト仕様書テンプレート
│   └── 04_guide.md                            ← 本ファイル
├── server/
│   ├── someip_common.py                        ← 共通モジュール (利用して良い)
│   └── vehicle_status_server.py                ← サンプルサーバ (提供される相手先のアプリケーションと想定)
├── client/
│   └── vehicle_status_client.py                ← クライアントスケルトン (★実装すべきアプリケーション)
└── tests/
    ├── test_unit.py                            ← ユニットテスト (★考える課題)
    └── test_integration.py                     ← 結合テスト (★考える課題)

```

## 4. 環境セットアップ

```bash
# Python バージョン確認 (3.9以上)
python3 --version

# pytest インストール (テスト用、venvで仮想化してから実施を推奨)
pip install pytest

# サーバ動作確認
python3 server/vehicle_status_server.py --scenario test
# → "=== 車両ステータスサーバ起動 ===" と表示されればOK
# → Ctrl+C で停止
```

## 5. 演習の進め方

### Step 1: 仕様書を読む (30分)

まず以下の2文書を読んでください。

1. **要件仕様書** (`01_SWE1_software_requirements_spec.md`)
   - クライアントが何をすべきかが書かれています
   - 各要件の「要件ID」を意識して読んでください
   - 本来は、アプリ開発者が作成します（上位文書としてシステム設計構想書が渡される想定）

2. **インターフェース仕様書** (`02_SWE2_SWE3_interface_spec.md`)
   - どう通信すべきかが書かれています
   - ペイロードのバイト構造を理解することが重要です

### Step 2: サーバを動かして観察する (15分)

```bash
# サーバを起動
python3 server/vehicle_status_server.py --scenario city

# 別ターミナルで、簡易的に受信してみる (動作確認)
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('127.0.0.1', 30491))
data, addr = s.recvfrom(4096)
print(f'受信: {len(data)} bytes from {addr}')
print(f'生データ: {data.hex()}')
s.close()
"
```

受信できたら、そのバイト列をインターフェース仕様書と照らし合わせて読み解いてみてください。

### Step 3: クライアントを実装する (2〜3時間)

`client/vehicle_status_client.py` の TODO 箇所を実装してください。

**推奨する実装順序:**

1. `_handle_received_message()` — メッセージ受信の振り分け
2. `_handle_notification()` — Notification受信と表示
3. `_validate_vehicle_status()` — データバリデーション
4. `_check_and_send_alerts()` と `_send_alert()` — アラート送信
5. `send_get_vehicle_status()` — Request/Response
6. `_handle_error()` — エラー処理

**ヒント:**
- `server/someip_common.py` の `SomeIpHeader`, `VehicleStatus` クラスを活用してください
- サーバのコード (`vehicle_status_server.py`) も参考になります
- 迷ったらインターフェース仕様書の通信シーケンス図を見てください

### Step 4: 動作確認 (30分)

```bash
# ターミナル1: サーバ起動
python3 server/vehicle_status_server.py --scenario city

# ターミナル2: クライアント起動
python3 client/vehicle_status_client.py
```

以下が確認できれば基本機能は完成です:
- 車両ステータスがコンソールに表示される
- サーバ側のログにアラート受信が表示される

### Step 5: テストを書く (1〜2時間)

`tests/test_unit.py` と `tests/test_integration.py` の TODO 箇所を実装してください。

```bash
# ユニットテスト実行 (サーバ不要)
pytest tests/test_unit.py -v

# 結合テスト実行 (サーバ起動が必要)
# ターミナル1:
python3 server/vehicle_status_server.py --scenario test
# ターミナル2:
pytest tests/test_integration.py -v

# 全テスト
pytest tests/ -v --tb=short
```

### Step 6: テスト仕様書を完成させる (30分)

`docs/03_SWE4_SWE5_test_spec.md` の以下を完成させてください:
- △ になっているテストケースの追加
- トレーサビリティマトリクスの完成
- 必要に応じた追加テストケースの記述

## 6. 評価ポイント

| 観点 | 内容 |
|------|------|
| 仕様準拠 | 要件仕様書の「必須」要件を全て満たしているか |
| コード品質 | エラーハンドリング、ログ出力が適切か |
| テスト品質 | 全必須要件にテストが紐づいているか、境界値テストがあるか |
| トレーサビリティ | 要件→テストの追跡ができる状態になっているか |

## 7. チャレンジ課題 (余裕がある人向け)

- Wiresharkでキャプチャし、仕様書との整合性を確認する（できればこれは実施してほしい）
- Notification受信数のスループットテストを実装する
- 複数クライアントを同時起動してサーバの挙動を確認する
- `--scenario` に新しいシナリオを追加する
