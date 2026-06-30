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


TOPI_URL = "https://topi.vn/lai-suat-vay-mua-nha.html"


def _topi_num(s: str):
    m = re.search(r"\d{1,3}(?:[.,]\d{1,2})?", (s or "").replace(",", "."))
    return float(m.group()) if m else None


def _topi_thang(s: str):
    """'24 tháng' → 24; '3 - 12 tháng' → 12 (lấy max); '5 năm' → 60; '-' → None."""
    if not s or s.strip() in ("-", ""):
        return None
    nums = [int(float(x)) for x in re.findall(r"\d{1,3}", s)]
    if not nums:
        return None
    v = max(nums)
    return v * 12 if "năm" in s.lower() else v


def fetch_topi() -> dict:
    """
    Cào bảng 'Lãi suất ưu đãi' topi.vn (render Playwright). Trả {name_lower: {...}}:
    lai_uu_dai (sàn của range 'Từ X - Y%'), uu_dai_thang, ky_han_max (năm),
    ltv (chỉ nhận khi text nói '% giá trị' để tránh '% nhu cầu vốn' gây hiểu nhầm), range, date.
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        pg.goto(TOPI_URL, timeout=45000, wait_until="domcontentloaded")
        try:
            pg.wait_for_selector("table tr td", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        pg.wait_for_timeout(1500)
        html = pg.content()
        br.close()

    dm = re.search(r"tháng\s*(\d{1,2})[/](20\d\d)", html)
    date = f"{dm.group(2)}-{int(dm.group(1)):02d}" if dm else None

    out: dict[str, dict] = {"_date": date}
    for tb in re.findall(r"<table[^>]*>.*?</table>", html, re.S):
        if "ưu đãi" not in tb.lower():
            continue
        for tr in re.findall(r"<tr[^>]*>.*?</tr>", tb, re.S):
            c = [unescape(re.sub(r"<[^>]+>", "", x)).strip()
                 for x in re.findall(r"<td[^>]*>.*?</td>", tr, re.S)]
            if len(c) < 5 or _topi_num(c[1]) is None:
                continue
            ltv = _topi_num(c[4])
            ltv_ok = ltv and "giá trị" in c[4].lower()      # bỏ '% nhu cầu vốn' (mơ hồ)
            out[c[0].lower()] = {
                "lai_uu_dai": _topi_num(c[1]),
                "range": re.sub(r"\s+", " ", c[1]),
                "uu_dai_thang": _topi_thang(c[2]),
                "ky_han_max": int(_topi_num(c[3])) if _topi_num(c[3]) else None,
                "ltv": min(ltv, 85) / 100 if ltv_ok else None,
            }
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

    # --- Lãi ƯU ĐÃI + thời hạn + LTV từ topi.vn (cho bank tư nhân topi có liệt kê) ---
    topi_updated = []
    try:
        topi = fetch_topi()
    except Exception:  # noqa: BLE001  — topi lỗi không được làm hỏng phần webgia
        topi = {}
    topi_date = topi.get("_date")
    for key, b in data["banks"].items():
        tname = (b.get("topi") or "").strip().lower()
        trow = topi.get(tname) if tname else None
        if not trow:
            continue
        if trow.get("lai_uu_dai"):
            b["lai_uu_dai"] = trow["lai_uu_dai"]
            b["lai_uu_dai_range"] = trow.get("range")
        if trow.get("uu_dai_thang"):
            b["uu_dai_thang"] = trow["uu_dai_thang"]
        if trow.get("ky_han_max"):
            b["ky_han_max"] = trow["ky_han_max"]
        if trow.get("ltv"):
            b["ltv_max"] = trow["ltv"]
        b["uu_dai_real"] = True
        b["nguon_uu_dai"] = f"topi.vn (T{topi_date})" if topi_date else "topi.vn"
        # topi cũng cho thời hạn/LTV → bỏ nhãn 'HouseNow' cũ nếu có
        b.pop("nguon", None)
        topi_updated.append(b["ten"])

    if updated or topi_updated:
        data["fetched_at"] = today
        data["is_demo"] = False
        data["topi_date"] = topi_date
        data["source"] = (f"Lãi thả nổi = LS tiền gửi (webgia.com) + biên độ; "
                          f"lãi ưu đãi/thời hạn/LTV từ topi.vn (T{topi_date}). Cào {today}.")
        save(data)
    return {"ok": bool(updated or topi_updated), "updated": updated,
            "topi_updated": topi_updated, "failed": failed,
            "fetched_at": data.get("fetched_at"), "topi_date": topi_date}


def main() -> None:
    if "--show" in sys.argv:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
        return
    res = run_fetch()
    if res["ok"]:
        print(f"✓ Lãi thả nổi (webgia, tiền gửi+biên độ): {', '.join(res['updated']) or '—'}")
        print(f"✓ Ưu đãi/thời hạn/LTV (topi.vn T{res.get('topi_date')}): "
              f"{', '.join(res.get('topi_updated', [])) or '—'}")
        print(f"Đã ghi {PATH}")
    else:
        print("Không cào được:", res.get("err", "không rõ"))


if __name__ == "__main__":
    main()
