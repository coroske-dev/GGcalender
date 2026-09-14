# GGcalender

ゴールドジム幕張3店舗（WBG / ANNEX / ベイパークアリーナ）の休館日を
Google カレンダーで購読できる `.ics` にするスクリプト。

## 仕組み

1. `gen_ics.py` が各店舗ページの定休ルール + ヘッダー告知（振替・臨時）から休館日を計算
2. `docs/gg_kyukan.ics` に書き出し → GitHub Pages で公開
3. Google カレンダー「URLで追加」で購読

## 更新

- 自動: GitHub Actions が毎月1日・15日に再生成（`.github/workflows/update.yml`）
- 手動: `python3 gen_ics.py` → `git commit` → `git push`
- 夏季・年末年始など告知が出たら `gen_ics.py` の `MANUAL_CLOSED` に日付を足す

## 予定の見え方

| 表記 | 意味 |
|---|---|
| 🚫 WBG 休館 | 定休ルール通りの休館 |
| ⚠️ ANNEX 休館（振替） | ルール上は営業日だが告知で休館になった日 |
| ✅ WBG 営業（振替） | ルール上は休館日だが告知で営業する日 |

## 出典

- https://www.goldsgym.jp/shop/makuhari-chiba-wbg/
- https://www.goldsgym.jp/shop/makuhari-chiba-annex/
- https://www.goldsgym.jp/shop/makuhari-baypark-arena/
- 祝日: 内閣府 https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv
