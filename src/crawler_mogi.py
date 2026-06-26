"""
Crawler nguồn THỨ BA: mogi.vn (server-render HTML, không cần Playwright).

LƯU Ý QUAN TRỌNG: trang danh sách mogi chỉ ghi địa chỉ tới mức QUẬN (không có phường),
và trộn nhiều quận trên 1 trang. Vì vậy dữ liệu mogi chỉ dùng được ở MỨC QUẬN
(district-level) để đối chiếu chéo — KHÔNG có phường (phuong = null).

    python src/crawler_mogi.py --pages 15 --out data/crawl_mogi.json
    python src/import_data.py data/crawl_mogi.json --append

Output cùng định dạng record với 2 crawler kia (title, raw_extra, dia_chi, url,
loai_bds, district_id, quan, source='mogi').
"""

import argparse, json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from districts import DISTRICTS, PRIORITY, from_addr

# Chỉ giữ mogi cho các quận đã có dữ liệu bds/chotot (đồng bộ, tránh quận chỉ-có-mogi)
TARGET = ["binh_thanh"] + PRIORITY

# loai_bds -> slug chuyên mục mogi (toàn TP.HCM, lọc quận client-side qua prop-addr)
CAT_URL = {
    "nha_rieng": "https://mogi.vn/mua-nha-rieng",
    "chung_cu": "https://mogi.vn/mua-can-ho-chung-cu",
    "dat_nen": "https://mogi.vn/mua-dat-nen-du-an",
}

# Tách từng card theo block prop-info
_CARD = re.compile(r'<div class="prop-info".*?<div class="price">(.*?)</div>', re.S)
_TITLE = re.compile(r'<h2 class="prop-title">(.*?)</h2>', re.S)
_HREF = re.compile(r'class="link-overlay" href="(.*?)"')
_ADDR = re.compile(r'class="prop-addr">(.*?)</div>', re.S)
_ATTR = re.compile(r'<li>(.*?)</li>', re.S)
_PRICE = re.compile(r'<div class="price">(.*?)</div>', re.S)


def _clean(s: str) -> str:
    s = re.sub(r"<sup>(.*?)</sup>", r"\1", s)   # m<sup>2</sup> -> m2
    s = re.sub(r"<.*?>", "", s)                 # bỏ tag còn lại
    return re.sub(r"\s+", " ", s).strip()


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")


def _parse_cards(html: str, loai_bds: str):
    out = []
    for block in re.findall(r'<div class="prop-info".*?</ul>\s*<div class="price">.*?</div>', html, re.S):
        title_m = _TITLE.search(block)
        href_m = _HREF.search(block)
        addr_m = _ADDR.search(block)
        price_m = _PRICE.search(block)
        attrs = [_clean(a) for a in _ATTR.findall(block)]
        if not (title_m and addr_m and price_m):
            continue
        addr = _clean(addr_m.group(1))
        did = from_addr(addr)
        if not did or did not in TARGET:         # ngoài bộ quận đang theo dõi -> bỏ
            continue
        # gộp giá + diện tích (+ PN) cho parser xử lý chung; thêm 'PN' đúng cú pháp parser
        size = next((a for a in attrs if "m2" in a or "m²" in a), "")
        pn = next((a for a in attrs if a.upper().endswith("PN")), "")
        extra = " ".join(filter(None, [_clean(price_m.group(1)), size,
                                        pn.replace(" ", "") if pn else ""]))
        out.append({
            "title": _clean(title_m.group(1)),
            "raw_extra": extra,
            "dia_chi": addr,                     # chỉ mức quận, không có phường
            "url": href_m.group(1) if href_m else None,
            "loai_bds": loai_bds,
            "district_id": did,
            "quan": DISTRICTS[did]["ten"],
            "source": "mogi",
        })
    return out


def crawl(pages: int, loai_bds_list=None, delay: float = 1.0):
    loai_bds_list = loai_bds_list or list(CAT_URL)
    out = []
    for loai in loai_bds_list:
        base = CAT_URL[loai]
        print(f"\n=== mogi: {loai} ({base}) ===")
        for cp in range(1, pages + 1):
            url = base if cp == 1 else f"{base}?cp={cp}"
            try:
                cards = _parse_cards(_fetch(url), loai)
                print(f"[{loai} trang {cp}/{pages}] {len(cards)} tin (thuộc quận theo dõi)")
                out.extend(cards)
            except Exception as e:
                print(f"   ! lỗi trang {cp}: {e}")
            time.sleep(delay)
    return [r for r in out if r.get("title")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=15, help="Số trang/loại (mỗi trang ~15 tin)")
    ap.add_argument("--out", default="data/crawl_mogi.json")
    ap.add_argument("--loai", nargs="*", choices=list(CAT_URL))
    args = ap.parse_args()
    rows = crawl(args.pages, loai_bds_list=args.loai)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu {len(rows)} tin -> {args.out}")
    print(f"Bước tiếp: python src/import_data.py {args.out} --append")


if __name__ == "__main__":
    main()
