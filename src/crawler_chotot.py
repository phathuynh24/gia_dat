"""
Crawler nguồn THỨ HAI: Chợ Tốt / Nhà Tốt (nhatot.com) qua API public.

Khác batdongsan (phải dùng Playwright vì JS + bot-protection), Chợ Tốt có API JSON
gọi thẳng được bằng HTTP — nhanh, ổn định, không cần trình duyệt.

    python src/crawler_chotot.py --pages 20 --out data/crawl_chotot.json
    python src/crawler_chotot.py --loai chung_cu dat_nen --pages 10

Output cùng định dạng với crawler batdongsan (title, raw_extra, dia_chi, url, loai_bds)
→ chạy chung pipeline:  python src/import_data.py data/crawl_chotot.json --append

LƯU Ý: API nội bộ của Chợ Tốt, có thể đổi. Chỉ lấy lượng nhỏ cho mục đích nội bộ.
"""

import argparse, json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from districts import DISTRICTS, PRIORITY

API = "https://gateway.chotot.com/v1/public/ad-listing"
REGION_HCM = 13000

# category Chợ Tốt -> loai_bds của ta
CATEGORIES = {
    "nha_rieng": 1020,   # Nhà ở
    "chung_cu": 1010,    # Căn hộ/Chung cư
    "dat_nen": 1040,     # Đất
}
PER_PAGE = 50


def _fetch(area: int, cg: int, offset: int, limit: int = PER_PAGE):
    url = (f"{API}?region_v2={REGION_HCM}&area_v2={area}"
           f"&cg={cg}&limit={limit}&o={offset}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _to_record(ad: dict, loai_bds: str, district_id: str):
    """Map 1 ad Chợ Tốt -> record raw giống crawler batdongsan."""
    price_string = ad.get("price_string") or ""
    size = ad.get("size")
    rooms = ad.get("rooms")
    # Gộp giá + diện tích (+ số PN cho chung cư) vào raw_extra để parser xử lý chung
    extra = price_string
    if size:
        extra += f" {size} m²"
    if loai_bds == "chung_cu" and rooms:
        extra += f" {rooms}PN"
    ward = ad.get("ward_name") or ad.get("ward_name_v3") or ""
    return {
        "title": ad.get("subject") or "",
        "raw_extra": extra.strip(),
        "dia_chi": f"{ward}, {ad.get('area_name','')}".strip(", "),
        "url": f"https://www.nhatot.com/mua-ban-{ad.get('list_id')}.htm",
        "loai_bds": loai_bds,
        "district_id": district_id,
        "quan": DISTRICTS[district_id]["ten"],
        "source": "chotot",   # tag nguồn để đối chiếu chéo giá
    }


def crawl(pages: int, districts=None, loai_bds_list=None, delay: float = 1.0):
    districts = districts or PRIORITY
    loai_bds_list = loai_bds_list or list(CATEGORIES)
    out = []
    for dist in districts:
        area = DISTRICTS[dist]["chotot"]
        for loai in loai_bds_list:
            cg = CATEGORIES[loai]
            print(f"\n=== Chợ Tốt: {DISTRICTS[dist]['ten']} / {loai} (area={area} cg={cg}) ===")
            for page in range(pages):
                offset = page * PER_PAGE
                try:
                    data = _fetch(area, cg, offset)
                    ads = data.get("ads", [])
                    print(f"[{dist}/{loai} trang {page+1}/{pages}] offset {offset}: {len(ads)} tin")
                    if not ads:
                        break
                    for ad in ads:
                        ps = (ad.get("price_string") or "").lower()
                        if "tháng" in ps or "thỏa thuận" in ps:   # bỏ tin CHO THUÊ
                            continue
                        out.append(_to_record(ad, loai, dist))
                except Exception as e:
                    print(f"   ! lỗi offset {offset}: {e}")
                time.sleep(delay)  # lịch sự với API
    return [r for r in out if r.get("title")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=10, help="Số trang/loại (mỗi trang 50 tin)")
    ap.add_argument("--out", default="data/crawl_chotot.json")
    ap.add_argument("--loai", nargs="*", choices=list(CATEGORIES),
                    help="Loại cần lấy (mặc định cả 3)")
    ap.add_argument("--district", nargs="*", choices=list(DISTRICTS),
                    help="Quận cần lấy (mặc định bộ giá mềm: %(default)s)" )
    args = ap.parse_args()

    rows = crawl(args.pages, districts=args.district, loai_bds_list=args.loai)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu {len(rows)} tin -> {args.out}")
    print(f"Bước tiếp: python src/import_data.py {args.out} --append")


if __name__ == "__main__":
    main()
