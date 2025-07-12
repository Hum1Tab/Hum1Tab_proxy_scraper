# Hum1Tab Proxy Scraper v1.0
<img width="1109" height="626" alt="image" src="https://github.com/user-attachments/assets/fa2d14c3-0b55-4176-9c23-6d4be1db9176" />


シンプル・高速なPython製プロキシスクレイパー。

## 特徴
- HTTP / SOCKS4 / SOCKS5 プロキシ対応
- メニュー操作で簡単取得
- 検証機能・重複除去
- 出力ファイル: `proxy/` フォルダ内に保存

## 使い方
1. 必要なPythonパッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
2. スクリプトを実行
   ```bash
   python Hum1Tab_proxy_scraper.py
   ```
3. メニューから操作
   - [1] HTTPプロキシ取得
   - [2] SOCKS4プロキシ取得
   - [3] SOCKS5プロキシ取得
   - [4] 全タイプ一括取得
   - [5] ソース管理
   - [6] ソースの動作チェック
   - [7] 設定
   - [8] 終了

## 設定
- `settings.json` で各種動作をカスタマイズ可能
- メニューの「設定」からも変更できます

## 出力例
- `proxy/http_proxies.txt`, `proxy/socks4_proxies.txt`, `proxy/socks5_proxies.txt`

## 注意
- 無料プロキシは安定性・匿名性が保証されません
- 利用は自己責任でお願いします

---
(c) Hum1Tab 2025
