"""
Nạp DỮ LIỆU MẪU (MOCK) vào DB để chạy thử dashboard — KHÔNG phải giá thật.

Chạy:  python src/seed.py            # ~120 tin mock
       python src/seed.py --n 200   # sinh nhiều hơn

Mỗi tin được sinh thành tiêu đề rao tiếng Việt thật-như-thật rồi cho qua parser
(giống hệt pipeline data thật). Khi có data crawl thật, dùng src/import_data.py.
"""

import argparse, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))

import db
from parser import parse_listing

# Giá/m² cơ sở (triệu/m²) cho HẺM XE HƠI theo phường — mock theo mặt bằng Bình Thạnh.
WARD_BASE = {
    "1": 130, "2": 150, "3": 120, "5": 115, "6": 105, "7": 110,
    "11": 125, "12": 80, "13": 105, "14": 78, "15": 110, "17": 95,
    "19": 100, "21": 90, "22": 130, "24": 100, "25": 105, "26": 95,
    "27": 82, "28": 88,
}
# Hệ số theo loại đường so với HXH
TYPE_FACTOR = {"mat_tien": 1.7, "hxh": 1.0, "hem": 0.72}

STREETS = {
    "mat_tien": ["Điện Biên Phủ", "Phan Văn Trị", "Nơ Trang Long", "Xô Viết Nghệ Tĩnh",
                 "Bạch Đằng", "Lê Quang Định", "Phan Đăng Lưu", "Nguyễn Hữu Cảnh", "D5", "D2"],
    "hxh": ["Đinh Bộ Lĩnh", "Nguyễn Xí", "Ung Văn Khiêm", "Bùi Đình Túy", "Chu Văn An",
            "Đặng Thùy Trâm", "Nguyễn Cửu Vân", "Vũ Tùng"],
    "hem": ["", "", ""],  # hẻm thường không ghi tên đường lớn
}
DIRECTIONS = ["Đông", "Tây", "Nam", "Bắc", "Đông Nam", "Tây Bắc", "Tây Nam", "Đông Bắc", None, None]


def _price_text(gia_ty: float) -> str:
    """Sinh chuỗi giá đa dạng: '6.5 tỷ', '7 tỷ 200', '850 triệu'."""
    if gia_ty < 1:
        return f"{int(round(gia_ty * 1000))} triệu"
    if random.random() < 0.35:
        ty = int(gia_ty)
        le = int(round((gia_ty - ty) * 1000))
        return f"{ty} tỷ {le}" if le else f"{ty} tỷ"
    return f"{round(gia_ty, 1)} tỷ"


def _make_listing(ward: str, loai: str):
    base = WARD_BASE[ward] * TYPE_FACTOR[loai] * random.uniform(0.85, 1.15)
    ngang = round(random.uniform(3.5, 6.0), 1)
    dai = round(random.uniform(12, 22), 0)
    dt = round(ngang * dai)
    gia = round(base * dt / 1000, 1)  # tỷ
    so_tang = random.choice([2, 3, 3, 4])
    huong = random.choice(DIRECTIONS)
    street = random.choice(STREETS[loai])

    if loai == "mat_tien":
        lead = f"Bán nhà mặt tiền {street}".strip()
    elif loai == "hxh":
        w = random.choice([5, 5, 6, 7])
        lead = f"Bán nhà HXH {w}m {street}".strip()
    else:
        w = random.choice([3, 3.5, 4])
        lead = f"Bán nhà hẻm {w}m"

    parts = [lead, f"P{ward}", f"{ngang}x{int(dai)}", f"{so_tang} tầng"]
    if huong:
        parts.append(f"hướng {huong}")
    parts.append(f"giá {_price_text(gia)}")
    return " ".join(parts)


def generate(n: int):
    rows = []
    wards = list(WARD_BASE)
    for _ in range(n):
        ward = random.choice(wards)
        loai = random.choices(["mat_tien", "hxh", "hem"], weights=[2, 4, 4])[0]
        title = _make_listing(ward, loai)
        parsed = parse_listing(title)
        # ~10% là giá đóng thật (team nhập tay)
        if random.random() < 0.1:
            parsed["source"] = "thuc_te"
            parsed["trang_thai"] = "da_ban"
            parsed["ghi_chu"] = "Giá đóng thật từ team"
        else:
            parsed["source"] = "crawl"
        rows.append(parsed)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120, help="Số tin mock cần sinh")
    ap.add_argument("--seed", type=int, default=42, help="Seed ngẫu nhiên (cố định để tái lập)")
    args = ap.parse_args()

    random.seed(args.seed)
    db.init_db()
    db.clear()
    rows = generate(args.n)
    n = db.insert_many(rows)
    ok = sum(1 for r in rows if r.get("gia") and r.get("dien_tich"))
    print(f"Đã nạp {len(rows)} tin MOCK (ghi {n} dòng, parse đủ giá+DT: {ok}). Tổng DB: {db.count()}")


if __name__ == "__main__":
    main()
