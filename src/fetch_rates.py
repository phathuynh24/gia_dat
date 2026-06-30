"""
Cập nhật lãi suất vay mua nhà → ghi data/bank_rates.json.

CÁCH LÀM (đã chốt với user): lãi vay THẢ NỔI của NHTM VN = LS tiết kiệm kỳ 12 tháng
+ biên độ (~3,5–4,5%/năm tuỳ bank). Ta cào LS TIẾT KIỆM THẬT (cập nhật hằng ngày) từ
webgia.com rồi cộng biên độ (`bien_do` trong JSON) → ra lãi thả nổi thật.
Lãi ƯU ĐÃI (campaign) không có trên bảng này nên giữ số curated.

⚠️ Nguồn free render bảng bằng JS + che số trong HTML tĩnh → PHẢI dùng Playwright
(trình duyệt thật). Cần: `pip install -r requirements-crawl.txt` + `playwright install chromium`.

CHẠY:
    python src/fetch_rates.py            # cào & cập nhật
    python src/fetch_rates.py --show     # in bảng hiện có
Hoặc bấm nút "Lấy lãi mới nhất" trên trang /vay-von (gọi run_fetch()).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from html import unescape

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bank_rates.json")
WEBGIA_URL = "https://webgia.com/lai-suat/"

# Vị trí cột (sau cột tên bank): KKH,1,3,6,9,[12],13,18,24,36 → index 5 = kỳ 12 tháng.
COL_12M = 5


def load() -> dict:
    with open(PATH, encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _num(s: str) -> float | None:
    """'5,90' / '5.90' → 5.9; '-' → None."""
    s = (s or "").strip().replace(",", ".")
    return float(s) if re.fullmatch(r"\d{1,2}\.\d{1,2}", s) else None


def fetch_savings() -> dict:
    """
    Cào LS tiết kiệm kỳ 12 tháng theo ngân hàng từ webgia.com (render bằng Playwright).
    Trả {ten_bank_chuan_hoa: ls_12m}. Raise nếu Playwright thiếu/không chạy được.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page.goto(WEBGIA_URL, timeout=45000, wait_until="networkidle")
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()

    out: dict[str, float] = {}
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
        cells = [unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>.*?</td>", tr, re.S)]
        if len(cells) < 7:
            continue
        name = cells[0]
        if not name or _num(name) is not None:        # bỏ hàng không phải tên bank
            continue
        vals = cells[1:]
        ls12 = _num(vals[COL_12M]) if len(vals) > COL_12M else None
        if ls12 is None:                              # fallback 13T / 24T nếu 12T trống
            for i in (COL_12M + 1, COL_12M + 3):
                if len(vals) > i and _num(vals[i]) is not None:
                    ls12 = _num(vals[i]); break
        if ls12:
            out.setdefault(name.lower(), ls12)        # giữ hàng đầu (thường KH cá nhân)
    return out


def run_fetch() -> dict:
    """Cào LS tiết kiệm thật → cập nhật lãi thả nổi mỗi bank. Fail-safe (không raise)."""
    data = load()
    today = datetime.date.today().isoformat()
    try:
        savings = fetch_savings()
    except ImportError:
        return {"ok": False, "updated": [], "failed": list(data["banks"]),
                "fetched_at": data.get("fetched_at"),
                "err": "Thiếu Playwright. Cài: pip install -r requirements-crawl.txt && playwright install chromium"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "updated": [], "failed": list(data["banks"]),
                "fetched_at": data.get("fetched_at"), "err": f"Cào lỗi: {repr(e)[:160]}"}

    updated, failed = [], []
    for key, b in data["banks"].items():
        wname = (b.get("webgia") or b["ten"]).lower()
        ls12 = savings.get(wname)
        if ls12 is None:                              # match lỏng: chứa tên
            for k, v in savings.items():
                if wname in k or k in wname:
                    ls12 = v; break
        if ls12 and b.get("bien_do"):
            b["ls_tiet_kiem_12m"] = ls12
            b["lai_tha_noi"] = round(ls12 + float(b["bien_do"]), 2)
            updated.append(b["ten"])
        else:
            failed.append(b["ten"])

    if updated:
        data["fetched_at"] = today
        data["is_demo"] = False
        data["source"] = (f"Lãi thả nổi = LS tiết kiệm 12T (webgia.com, cào {today}) "
                          f"+ biên độ. Lãi ưu đãi là mức tham khảo (campaign).")
        save(data)
    return {"ok": bool(updated), "updated": updated, "failed": failed,
            "fetched_at": data.get("fetched_at")}


def main() -> None:
    if "--show" in sys.argv:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
        return
    res = run_fetch()
    if res["ok"]:
        print(f"✓ Cập nhật lãi thả nổi (từ LS tiết kiệm thật): {', '.join(res['updated'])}")
        if res["failed"]:
            print(f"  (không khớp tên trên webgia: {', '.join(res['failed'])})")
        print(f"Đã ghi {PATH}")
    else:
        print("Không cào được:", res.get("err", "không rõ"))


if __name__ == "__main__":
    main()
