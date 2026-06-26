"""
Parse data thô từ crawler -> nạp vào DB.

Chạy:
    python src/import_data.py data/crawl_raw.json
    python src/import_data.py data/crawl_raw.json --append   # giữ data cũ
    python src/import_data.py data/crawl_raw.json --claude    # parse bằng Claude API (cần key)

Cũng nhận CSV (cột tối thiểu: title; tùy chọn: dia_chi, url, source).
"""

import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

import db


def load_rows(path):
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--append", action="store_true", help="Không xóa data cũ")
    ap.add_argument("--claude", action="store_true", help="Parse bằng Claude API (cần ANTHROPIC_API_KEY)")
    args = ap.parse_args()

    from parser import parse_crawled, is_valid_listing

    raw = load_rows(args.path)
    rows, seen = [], set()
    junk = {}  # đếm lý do bị loại
    for r in raw:
        url = r.get("url")
        if url and url in seen:   # bỏ tin trùng (lặp giữa các trang)
            continue
        if url:
            seen.add(url)
        if args.claude:
            from parser import parse_with_claude
            parsed = parse_with_claude(r.get("title", ""), r.get("raw_extra", ""))
            parsed["dia_chi"] = r.get("dia_chi")
            parsed["url"] = url
            if r.get("loai_bds"):
                parsed["loai_bds"] = r["loai_bds"]
        else:
            parsed = parse_crawled(r)
        parsed["source"] = r.get("source") or "crawl"
        # Đa quận: lấy district_id/quan từ record (crawler đã tag); mặc định Bình Thạnh
        parsed["district_id"] = r.get("district_id") or "binh_thanh"
        if r.get("quan"):
            parsed["quan"] = r["quan"]
        parsed["ward_id"] = parsed.get("phuong")

        ok, ly_do = is_valid_listing(parsed)   # SRS Bước 1 — lọc tin rác
        if not ok:
            junk[ly_do] = junk.get(ly_do, 0) + 1
            continue
        rows.append(parsed)

    db.init_db()
    if not args.append:
        db.clear()
    n = db.insert_many(rows)
    junk_str = ", ".join(f"{k}={v}" for k, v in junk.items()) or "0"
    print(f"Nạp {len(rows)} tin sạch (ghi {n} dòng). Đã loại rác: {sum(junk.values())} ({junk_str}). "
          f"Tổng DB: {db.count()}")


if __name__ == "__main__":
    main()
