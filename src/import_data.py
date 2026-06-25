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

    from parser import parse_crawled

    raw = load_rows(args.path)
    rows, seen = [], set()
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
        else:
            parsed = parse_crawled(r)
        parsed["source"] = r.get("source") or "crawl"
        rows.append(parsed)

    db.init_db()
    if not args.append:
        db.clear()
    n = db.insert_many(rows)
    parsed_ok = sum(1 for r in rows if r.get("gia") and r.get("dien_tich"))
    print(f"Nạp {len(rows)} tin (ghi {n} dòng). Parse đủ giá+DT: {parsed_ok}/{len(rows)}. "
          f"Tổng DB: {db.count()}")


if __name__ == "__main__":
    main()
