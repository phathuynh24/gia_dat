"""
Cào DANH MỤC DỰ ÁN chung cư (sơ cấp) từ batdongsan → bảng `projects`.

Khác `crawler.py` (tin rao thứ cấp): đây là mục "dự án" — mỗi dự án có TRẠNG THÁI
(sắp/đang mở bán, đã bàn giao), để mua trực tiếp từ CĐT (giá tốt hơn mua qua tay).

Render bằng Playwright (trang JS + lazy-load khi cuộn). Toàn TP.HCM, phân trang /pN.

CHẠY:
    python src/crawler_duan.py --pages 10
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
from html import unescape

sys.path.insert(0, os.path.dirname(__file__))
import db  # noqa: E402
import districts  # noqa: E402

BASE = "https://batdongsan.com.vn/du-an-can-ho-chung-cu-tp-hcm"

STATUS_MAP = [
    ("Đang mở bán", "dang_mo_ban"),
    ("Sắp mở bán", "sap_mo_ban"),
    ("Đã bàn giao", "da_ban_giao"),
    ("Đang cập nhật", "dang_cap_nhat"),
]


def _txt(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def _quan_phuong(addr: str):
    """Trích quận + phường từ địa chỉ '..., Phường X, Quận Y, Hồ Chí Minh'."""
    quan = phuong = None
    mq = re.search(r"(Quận\s+[\w\d]+|Huyện\s+[\wÀ-ỹ\s]+?|TP\.?\s*Thủ Đức|Thành phố Thủ Đức)\s*,",
                   addr)
    if mq:
        quan = re.sub(r"\s+", " ", mq.group(1)).strip()
    mp = re.search(r"(Phường\s+[\w\d]+|Xã\s+[\wÀ-ỹ\s]+?|Thị trấn\s+[\wÀ-ỹ\s]+?)\s*,", addr)
    if mp:
        phuong = re.sub(r"\s+", " ", mp.group(1)).strip()
    return quan, phuong


def _parse_cards(html: str) -> list[dict]:
    # Mỗi card bắt đầu bằng class 're__prj-card-full'. Cắt theo mốc đó.
    chunks = html.split("re__prj-card-full")[1:]
    out = []
    for ch in chunks:
        m = re.search(r'href="(/du-an[^"]+?-pj\d+)"[^>]*title="([^"]+)"', ch)
        if not m:
            continue
        url = "https://batdongsan.com.vn" + m.group(1)
        ten = unescape(m.group(2)).strip()
        # trạng thái: lấy cụm xuất hiện sớm nhất trong card
        status = "dang_cap_nhat"
        best = len(ch)
        for label, code in STATUS_MAP:
            i = ch.find(label)
            if 0 <= i < best:
                best, status = i, code
        # địa chỉ nằm trong title của div location: <div class="re__prj-card-location" title="...">
        ma = re.search(r're__prj-card-location"[^>]*title="([^"]+)"', ch)
        if not ma:
            ma = re.search(r'>\s*([^<>]*?(?:Quận|Huyện|Xã)[^<>]*?Hồ Chí Minh)\s*<', ch)
        addr = unescape(ma.group(1)).strip() if ma else None
        quan, phuong = _quan_phuong(addr or "")
        # quy mô: các re__prj-card-config-value
        cfg = [_txt(x) for x in re.findall(r"re__prj-card-config-value[^>]*>(.*?)</", ch, re.S)]
        cfg = [c for c in cfg if c][:4]
        out.append({
            "ten": ten, "trang_thai": status, "url": url,
            "dia_chi": addr, "quan": quan, "phuong": phuong,
            "district_id": districts.from_addr(addr),
            "quy_mo": " · ".join(cfg) or None,
            "gia_info": None, "chu_dau_tu": None, "mo_ta": None,
            "source": "batdongsan",
        })
    return out


def _parse_featured(html: str) -> list[dict]:
    """Card 'nổi bật' (swiper re__prj-item) — CÓ nhãn trạng thái thật (Đang/Sắp mở bán),
    nhưng trộn toàn quốc → CHỈ giữ dự án HCM (địa chỉ chứa 'Hồ Chí Minh')."""
    out = []
    for m in re.finditer(r'<a class="re__prj-item[^"]*"[^>]*href="(/du-an[^"]+?-pj\d+)"(.*?)</a>',
                         html, re.S):
        url = "https://batdongsan.com.vn" + m.group(1)
        inner = m.group(2)
        nm = re.search(r'title="([^"]+)"', inner)
        ten = unescape(nm.group(1)).strip() if nm else None
        st = re.search(r're__prj-tag-info"?\s*>\s*<label>(.*?)</label>', inner, re.S)
        status_txt = _txt(st.group(1)) if st else ""
        ad = re.search(r're__prj-address[^>]*>(.*?)</div>', inner, re.S)
        addr = _txt(ad.group(1)) if ad else ""
        if "Hồ Chí Minh" not in addr or not ten:        # chỉ HCM
            continue
        code = next((c for label, c in STATUS_MAP if label in status_txt), "dang_cap_nhat")
        quan, phuong = _quan_phuong(addr)
        out.append({
            "ten": ten, "trang_thai": code, "url": url, "dia_chi": addr,
            "quan": quan, "phuong": phuong, "district_id": districts.from_addr(addr),
            "quy_mo": None, "gia_info": None, "chu_dau_tu": None, "mo_ta": None,
            "source": "batdongsan",
        })
    return out


def crawl(pages: int = 10) -> list[dict]:
    from playwright.sync_api import sync_playwright
    seen, rows = set(), []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        for n in range(1, pages + 1):
            url = BASE if n == 1 else f"{BASE}/p{n}"
            try:
                pg.goto(url, timeout=45000, wait_until="domcontentloaded")
                for _ in range(10):
                    pg.mouse.wheel(0, 5000)
                    pg.wait_for_timeout(700)
                html = pg.content()
            except Exception as e:  # noqa: BLE001
                print(f"  trang {n} lỗi: {repr(e)[:80]}")
                continue
            page_cards = _parse_cards(html)
            if n == 1:
                page_cards += _parse_featured(html)   # card nổi bật chỉ ở trang 1
            cards = [c for c in page_cards if c["url"] not in seen]
            for c in cards:
                seen.add(c["url"])
            rows += cards
            print(f"  trang {n}: +{len(cards)} dự án (tổng {len(rows)})")
            if not _parse_cards(html):                 # hết list chính → dừng
                break
        b.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=10)
    args = ap.parse_args()
    db.init_db()
    rows = crawl(args.pages)
    today = datetime.date.today().isoformat()
    for r in rows:
        r["fetched_at"] = today
    db.upsert_projects(rows)
    from collections import Counter
    print(f"\nĐã nạp {len(rows)} dự án. Trạng thái:",
          dict(Counter(r["trang_thai"] for r in rows)))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
