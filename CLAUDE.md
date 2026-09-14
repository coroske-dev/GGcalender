# GGcalender プロジェクトメモ

ゴールドジム幕張3店舗の休館日を Google カレンダーで購読できる ICS にする。
利用者本人向け（1人用）。詳細は README.md、経緯は 調査メモ_休館日カレンダー.md。

## 場所・URL

- GitHub: https://github.com/coroske-dev/GGcalender （Public、Pages は main の /docs）
- 購読URL: https://coroske-dev.github.io/GGcalender/gg_kyukan.ics
- Google カレンダー名: 「GG休館日」（URLで追加した購読カレンダー）
- `gh` コマンドは Homebrew ではなく `~/bin/gh` に直置き（coroske-dev でログイン済み、workflow スコープ付き）

## 更新の手順

- 自動: GitHub Actions が毎月1日・15日 06:00 JST に `gen_ics.py` を実行してコミット
- 手動: `python3 gen_ics.py` → 内容確認 → `git commit` → `git push`（`~/bin/gh` の認証で通る）
- 夏季・年末年始: `gen_ics.py` 冒頭の `MANUAL_CLOSED` に追記
- Actions が失敗したら告知文の解釈エラーの可能性。店舗ページを目視して `parse_notice` を直す

## 仕様の要点（公式ページ 2026-09-14 時点）

- ANNEX: 第2月曜休館。祝日なら営業し別日に振替（告知で判断）
- WBG: 月曜のうち「ANNEX が休館でない日」が休館（公式:「ANNEXの休館日に準じて営業」）
- ベイパーク: 第3月曜休館。祝日なら営業と推測（未確認、告知で上書きされる）
- 臨時・振替はニュース記事ではなく、店舗ページ上部 `<p class="header-sub__notice">` の1行にしか出ない
- 祝日は内閣府CSV https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv

## 表記ルール

🚫 店名 休館 / ⚠️ 店名 休館（振替） / ✅ 店名 営業（振替）。終日予定、店名は WBG / ANNEX / ベイパーク。
