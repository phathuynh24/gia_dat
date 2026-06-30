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

# Vị trí cột (sau cột tên bank): KKH,1,3,6,9,[12],13,18,[24],36.
COL_12M = 5
COL_24M = 8


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
        # 'networkidle' hay timeout vì webgia giữ kết nối (ads/analytics) → dùng
        # 'domcontentloaded' rồi chờ bảng render xong.
        page.goto(WEBGIA_URL, timeout=45000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("table tr td", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()

    out: dict[str, dict] = {}
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
        ls24 = _num(vals[COL_24M]) if len(vals) > COL_24M else None
        if ls12 or ls24:
            out.setdefault(name.lower(), {"12": ls12, "24": ls24})   # giữ hàng đầu (KH cá nhân)
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
        # Match CHÍNH XÁC theo tên webgia (case-insensitive). KHÔNG match lỏng/substring —
        # 'mb' là substring của 'techco(mb)ank'/'saco(mb)ank' → từng gây lấy nhầm lãi MB.
        wname = (b.get("webgia") or "").strip().lower()
        srow = savings.get(wname) if wname else None
        # Kỳ tham chiếu lãi thả nổi: '12' / '24' (theo công thức bank). 'co_so' → không
        # phải lãi tiền gửi (dùng tạm 12T làm xấp xỉ, đánh dấu ước tính).
        ref = str(b.get("ky_han_tham_chieu") or "12")
        # Chỉ suy được lãi thả nổi THẬT khi cơ sở là LÃI TIỀN GỬI (12T/24T) — webgia có.
        # Bank dùng 'lãi cơ sở' (MB/ACB/VPBank): webgia không có lãi cơ sở → KHÔNG bịa từ tiền gửi
        # (từng ra thả nổi < ưu đãi, vô lý) → fallback baseline curated, nhãn tham khảo.
        base = srow.get(ref) if (srow and ref in ("12", "24")) else None
        if base and b.get("bien_do"):
            b["ls_tham_chieu"] = base
            b["ls_ky_han"] = "24T" if ref == "24" else "12T"
            b.pop("tha_noi_uoc_tinh", None)
            b["lai_tha_noi"] = round(base + float(b["bien_do"]), 2)
            b["lai_real"] = True
            updated.append(b["ten"])
        else:
            for f in ("ls_tham_chieu", "ls_ky_han", "ls_tiet_kiem_12m", "tha_noi_uoc_tinh"):
                b.pop(f, None)
            if b.get("lai_tha_noi_goc") is not None:   # khôi phục lãi curated (tránh giữ số sai cũ)
                b["lai_tha_noi"] = b["lai_tha_noi_goc"]
            b["lai_real"] = False
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
