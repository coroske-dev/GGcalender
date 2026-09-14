#!/usr/bin/env python3
"""
ゴールドジム幕張3店舗（WBG / ANNEX / ベイパークアリーナ）の休館日を
公式ページの定休ルール + ヘッダー告知（振替・臨時）から計算し、
Google カレンダーで購読できる .ics を docs/gg_kyukan.ics に書き出す。

使い方:  python3 gen_ics.py
依存:    Python 標準ライブラリのみ
"""
import datetime as dt
import re
import sys
import urllib.request
from pathlib import Path

# ------------------------------------------------------------
# 設定
# ------------------------------------------------------------
BASE = "https://www.goldsgym.jp/shop/"
STORES = {
    # key: (表示名, ページslug)
    "annex": ("ANNEX", "makuhari-chiba-annex"),
    "wbg": ("WBG", "makuhari-chiba-wbg"),
    "baypark": ("ベイパーク", "makuhari-baypark-arena"),
}
HOLIDAY_CSV = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
OUT = Path(__file__).parent / "docs" / "gg_kyukan.ics"
MONTHS_AHEAD = 3  # 今月 + 何か月先まで出すか

# 手動で追加する休館日（夏季・年末年始など、告知が出たらここに足す）
# 形式: (日付"YYYY-MM-DD", 店舗key or "all", メモ)
MANUAL_CLOSED = [
    # ("2026-12-31", "all", "年末年始休館（全店）"),
]

# ------------------------------------------------------------
# 取得まわり
# ------------------------------------------------------------
UA = {"User-Agent": "Mozilla/5.0 (GGcalender ics generator)"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load_holidays() -> set:
    """内閣府CSV（cp932）から祝日・休日の集合を作る"""
    text = fetch(HOLIDAY_CSV).decode("cp932")
    days = set()
    for line in text.splitlines()[1:]:
        d, _, _ = line.partition(",")
        y, m, dd = d.split("/")
        days.add(dt.date(int(y), int(m), int(dd)))
    return days


def fetch_notice(slug: str) -> str:
    """店舗ページ上部の告知1行を返す。見つからなければ例外"""
    html = fetch(BASE + slug + "/").decode("utf-8", "ignore")
    m = re.search(r'class="header-sub__notice">(.*?)</p>', html, re.S)
    if not m:
        raise RuntimeError(f"{slug}: header-sub__notice が見つからない（サイト構造変更?）")
    return re.sub(r"\s+", " ", m.group(1)).strip()


# ------------------------------------------------------------
# 日付ユーティリティ
# ------------------------------------------------------------
def month_range(start: dt.date, months: int):
    """start の月初から months か月後の月末まで"""
    first = start.replace(day=1)
    y, m = first.year, first.month + months + 1
    while m > 12:
        y, m = y + 1, m - 12
    last = dt.date(y, m, 1) - dt.timedelta(days=1)
    return first, last


def nth_monday(d: dt.date) -> int:
    """その日が第何月曜か（月曜でなければ0）"""
    return 0 if d.weekday() != 0 else (d.day - 1) // 7 + 1


def parse_dates(text: str, today: dt.date) -> list:
    """'10月5日' や '9/14' を date に。年は「直近の未来」で補う"""
    out = []
    for mm, dd in re.findall(r"(\d{1,2})[月/](\d{1,2})", text):
        mm, dd = int(mm), int(dd)
        y = today.year
        if mm < today.month - 1:  # 先月より前なら来年扱い
            y += 1
        try:
            out.append(dt.date(y, mm, dd))
        except ValueError:
            pass
    return out


def parse_notice(notice: str, today: dt.date):
    """告知文を「休館する日」「営業する日」に分ける。
    ※ で区切った各断片に 休館/営業 のどちらの語があるかで判定"""
    closed, opened, warn = [], [], []
    for seg in re.split(r"[※]", notice):
        ds = parse_dates(seg, today)
        if not ds:
            continue
        has_c, has_o = "休館" in seg, "営業" in seg
        if has_o and not has_c:
            opened += ds
        elif has_c and not has_o:
            closed += ds
        else:
            warn.append(seg.strip())
    return closed, opened, warn


# ------------------------------------------------------------
# 休館日の計算
# ------------------------------------------------------------
def rule_closed(store: str, d: dt.date, hol: set) -> bool:
    """公式ページの定休ルールだけで判定"""
    n = nth_monday(d)
    if n == 0:
        return False
    is_hol = d in hol
    if store == "annex":  # 第2月曜。祝日なら営業
        return n == 2 and not is_hol
    if store == "wbg":  # 第1,3,4,5月曜。第2月曜が祝日なら休館
        return n != 2 or is_hol
    if store == "baypark":  # 第3月曜。祝日なら営業（バナーからの推測・未確認）
        return n == 3 and not is_hol
    return False


def build(today: dt.date):
    first, last = month_range(today, MONTHS_AHEAD)
    hol = load_holidays()
    days = [first + dt.timedelta(i) for i in range((last - first).days + 1)]

    notices, overrides, warns = {}, {}, []
    for key, (_, slug) in STORES.items():
        notices[key] = fetch_notice(slug)
        c, o, w = parse_notice(notices[key], today)
        overrides[key] = (set(c), set(o))
        warns += [f"{key}: 解釈できない断片 → {x}" for x in w]

    pure, final = {}, {}
    # 1) ANNEX と ベイパーク: ルール → 告知で上書き
    for key in ("annex", "baypark"):
        pure[key] = {d for d in days if rule_closed(key, d, hol)}
        c, o = overrides[key]
        final[key] = (pure[key] | c) - o
    # 2) WBG: 月曜のうち ANNEX が休館でない日が休館（公式:「ANNEXの休館日に準じて営業」）
    pure["wbg"] = {d for d in days if rule_closed("wbg", d, hol)}
    c, o = overrides["wbg"]
    final["wbg"] = ({d for d in days if d.weekday() == 0} - final["annex"] | c) - o

    # 3) 手動追加
    for s, key, note in MANUAL_CLOSED:
        d = dt.date.fromisoformat(s)
        if not (first <= d <= last):
            continue
        for k in (STORES if key == "all" else [key]):
            final[k].add(d)

    return pure, final, notices, warns, first, last


# ------------------------------------------------------------
# ICS 出力
# ------------------------------------------------------------
def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\;").replace("\n", "\\n")


def fold(line: str) -> str:
    """RFC5545: 1行75バイト以内に折り返す（マルチバイト文字は途中で切らない）"""
    out, cur, n = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        if n + b > (75 if not out else 74):
            out.append(cur)
            cur, n = ch, b
        else:
            cur, n = cur + ch, n + b
    out.append(cur)
    return "\n ".join(out)


def vevent(uid, d, summary, desc, stamp):
    return "\n".join(fold(x) for x in [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
        f"DTEND;VALUE=DATE:{d + dt.timedelta(1):%Y%m%d}",
        f"SUMMARY:{esc(summary)}",
        f"DESCRIPTION:{esc(desc)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ])


def write_ics(pure, final, notices, today):
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    events = []
    for key, (name, slug) in STORES.items():
        src = f"出典: {BASE}{slug}/\n告知: {notices[key]}\n生成: {today}"
        for d in sorted(final[key] | pure[key]):
            in_final, in_pure = d in final[key], d in pure[key]
            if in_final and in_pure:
                summ = f"🚫 {name} 休館"
            elif in_final:
                summ = f"⚠️ {name} 休館（振替）"
            else:
                summ = f"✅ {name} 営業（振替）"
            events.append(vevent(f"{key}-{d:%Y%m%d}@ggcalender", d, summ, src, stamp))
    body = "\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GGcalender//JP",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:GG休館日",
        "X-WR-TIMEZONE:Asia/Tokyo",
        *events,
        "END:VCALENDAR",
    ]) + "\n"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(body.replace("\n", "\r\n"), encoding="utf-8")
    return len(events)


def main():
    today = dt.date.today()
    pure, final, notices, warns, first, last = build(today)
    n = write_ics(pure, final, notices, today)

    print(f"期間: {first} 〜 {last}   予定数: {n}   出力: {OUT}")
    for key, (name, _) in STORES.items():
        print(f"\n[{name}] 告知: {notices[key]}")
        for d in sorted(final[key] | pure[key]):
            tag = "休館" if d in final[key] and d in pure[key] else \
                  "休館（振替）" if d in final[key] else "営業（振替）"
            print(f"  {d} ({'月火水木金土日'[d.weekday()]}) {tag}")
    if warns:
        print("\n!! 警告（告知の一部を解釈できず。サイトを目視確認してください）")
        for w in warns:
            print("  -", w)
        sys.exit(2)


if __name__ == "__main__":
    main()
