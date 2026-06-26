"""
Chụp mốc giá (snapshot) để dựng LỊCH SỬ giá theo thời gian (SRS Mở rộng 4).

Cách dùng:
    python src/snapshot.py                 # chụp mốc THẬT cho hôm nay (source=real)
    python src/snapshot.py --ngay 2026-06-01   # chụp với ngày chỉ định
    python src/snapshot.py --demo --months 6   # sinh 6 mốc lịch sử MINH HOẠ (source=demo)
    python src/snapshot.py --clear-demo        # xoá hết mốc demo

Muốn có xu hướng THẬT: chạy lệnh chụp (không --demo) định kỳ (vd cron hàng tuần/tháng)
sau mỗi đợt crawl. Mỗi mốc lưu median giá/m² theo (loại BĐS, phường).
"""

import argparse, datetime, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))

import db


def gen_demo(months: int, seed: int = 7):
    """
    Sinh mốc lịch sử MINH HOẠ: lùi `months` tháng từ median hiện tại, mô phỏng giá
    tăng dần theo thời gian (mốc càng xa quá khứ giá càng thấp) + nhiễu nhỏ.
    Đánh dấu source='demo' để KHÔNG lẫn với mốc thật.
    """
    random.seed(seed)
    db.init_db()
    # Lấy median hiện tại làm mốc "hôm nay"
    today = datetime.date.today()
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT district_id, loai_bds, phuong, gia_per_m2 FROM listings
               WHERE gia_per_m2 IS NOT NULL AND phuong IS NOT NULL AND loai_bds IS NOT NULL"""
        ).fetchall()
    from statistics import median
    groups = {}
    for r in rows:
        groups.setdefault((r["district_id"], r["loai_bds"], r["phuong"]), []).append(r["gia_per_m2"])
    base = {k: median(v) for k, v in groups.items() if len(v) >= 3}

    total = 0
    # months mốc quá khứ + mốc hôm nay
    for m in range(months, -1, -1):
        d = (today.replace(day=15) - datetime.timedelta(days=30 * m)).isoformat()
        # giá quá khứ thấp hơn: giảm ~1.5%/tháng so với hiện tại + nhiễu ±1.5%
        decay = (1 - 0.015) ** m
        batch = []
        for (dist, lb, ph), med in base.items():
            val = round(med * decay * random.uniform(0.985, 1.015), 1)
            n = len(groups[(dist, lb, ph)])
            batch.append((d, dist, lb, ph, val, n, "demo"))
        with db.get_conn() as conn:
            conn.execute("DELETE FROM price_snapshots WHERE ngay=? AND source='demo'", (d,))
            conn.executemany(
                "INSERT INTO price_snapshots (ngay, district_id, loai_bds, phuong, median_m2, n, source) "
                "VALUES (?,?,?,?,?,?,?)", batch)
        total += len(batch)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ngay", help="Ngày chụp (YYYY-MM-DD), mặc định hôm nay")
    ap.add_argument("--demo", action="store_true", help="Sinh mốc lịch sử minh hoạ")
    ap.add_argument("--months", type=int, default=6, help="Số tháng lịch sử khi --demo")
    ap.add_argument("--clear-demo", action="store_true", help="Xoá hết mốc demo")
    args = ap.parse_args()

    db.init_db()
    if args.clear_demo:
        with db.get_conn() as conn:
            n = conn.execute("DELETE FROM price_snapshots WHERE source='demo'").rowcount
        print(f"Đã xoá {n} mốc demo.")
        return
    if args.demo:
        n = gen_demo(args.months)
        print(f"Đã sinh {n} dòng mốc DEMO ({args.months + 1} mốc). Mở /xu-huong để xem.")
        return
    n = db.record_snapshot(ngay=args.ngay)
    print(f"Đã chụp mốc THẬT ngày {args.ngay or 'hôm nay'}: {n} dòng (loại×phường). "
          f"Tổng mốc: {len(db.snapshot_dates())}")


if __name__ == "__main__":
    main()
