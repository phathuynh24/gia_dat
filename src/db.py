"""
Lớp dữ liệu: SQLite làm database (đủ dùng cho <5,000 bản ghi như plan MVP).

Schema bám theo plan: địa chỉ, phường, loại đường, rộng hẻm, diện tích, số tầng,
hướng, giá rao, ngày đăng, trạng thái, ghi chú, lat/lng, giá/m² (tính sẵn).
"""

from __future__ import annotations  # cho phép cú pháp dict | None trên Python 3.9

import os
import sqlite3
from statistics import quantiles, median

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "listings.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    DEFAULT 'crawl',   -- 'crawl' | 'thuc_te' (giá đóng thật)
    loai_bds    TEXT    DEFAULT 'nha_rieng', -- 'nha_rieng' | 'chung_cu' | 'dat_nen'
    tieu_de     TEXT,
    dia_chi     TEXT,
    quan        TEXT    DEFAULT 'Bình Thạnh',
    district_id TEXT    DEFAULT 'binh_thanh',  -- chuẩn bị scale đa quận (IA v2 Bước 3)
    ward_id     TEXT,                          -- mã phường (hiện = số phường)
    street_id   TEXT,                          -- mã tuyến đường (chưa có data → null)
    phuong      TEXT,
    loai_duong  TEXT,                       -- 'mat_tien' | 'hxh' | 'hem' (nhà/đất)
    rong_hem    REAL,
    du_an       TEXT,                        -- tên dự án (chung cư)
    so_pn       INTEGER,                     -- số phòng ngủ (chung cư)
    dien_tich   REAL,                       -- m2
    ngang       REAL,
    dai         REAL,
    so_tang     INTEGER,                     -- số tầng nhà / tầng căn hộ trong toà
    huong       TEXT,
    gia         REAL,                        -- tỷ đồng
    gia_per_m2  REAL,                        -- triệu đồng/m2
    ngay_dang   TEXT,
    trang_thai  TEXT    DEFAULT 'dang_ban',
    ghi_chu     TEXT,
    lat         REAL,
    lng         REAL,
    url         TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- Lịch sử giá theo mốc thời gian (SRS Mở rộng 4) — mỗi lần chụp snapshot ghi 1 batch.
CREATE TABLE IF NOT EXISTS price_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ngay        TEXT,                       -- YYYY-MM-DD
    district_id TEXT    DEFAULT 'binh_thanh',
    loai_bds    TEXT,
    phuong      TEXT,
    median_m2   REAL,                       -- triệu/m2
    n           INTEGER,
    source      TEXT    DEFAULT 'real'      -- 'real' (chụp thật) | 'demo' (minh hoạ)
);

-- Dự án chung cư sơ cấp (đang/sắp mở bán) — để mua trực tiếp từ CĐT (giá tốt hơn thứ cấp).
-- Nguồn: batdongsan mục 'dự án' (crawler_duan.py). Khác listings (tin rao thứ cấp).
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ten         TEXT    NOT NULL,
    trang_thai  TEXT,                        -- 'sap_mo_ban' | 'dang_mo_ban' | 'da_ban_giao' | 'dang_cap_nhat'
    chu_dau_tu  TEXT,
    quan        TEXT,
    district_id TEXT,
    phuong      TEXT,
    dia_chi     TEXT,
    quy_mo      TEXT,                         -- diện tích/số căn/số block (text thô)
    gia_info    TEXT,                         -- giá dự kiến (text, thường 'đang cập nhật')
    mo_ta       TEXT,
    url         TEXT    UNIQUE,
    source      TEXT    DEFAULT 'batdongsan',
    fetched_at  TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);
"""

# Nhãn trạng thái dự án (sơ cấp)
TRANG_THAI_DA = {
    "sap_mo_ban": "🟡 Sắp mở bán",
    "dang_mo_ban": "🟢 Đang mở bán",
    "da_ban_giao": "🔵 Đã bàn giao",
    "dang_cap_nhat": "⚪ Đang cập nhật",
}

LOAI_DUONG_LABEL = {
    "mat_tien": "Mặt tiền",
    "hxh": "Hẻm xe hơi",
    "hem": "Hẻm",
}

# Loại bất động sản — mỗi loại có thuộc tính + đơn vị giá khác nhau (xem dashboard tabs)
LOAI_BDS_LABEL = {
    "chung_cu": "🏢 Chung cư",
    "nha_rieng": "🏠 Nhà riêng",
    "dat_nen": "🟫 Đất nền",
}
LOAI_BDS_DEFAULT = "chung_cu"

# Nhãn nguồn dữ liệu (để đối chiếu chéo giá giữa các site)
SOURCE_LABEL = {
    "batdongsan": "Batdongsan",
    "chotot": "Chợ Tốt",
    "mogi": "Mogi",
    "thuc_te": "Giá thật",
    "crawl": "Rao",
}


def _migrate(conn):
    """Thêm cột mới cho DB cũ (945 tin nhà riêng đã crawl trước khi có loai_bds)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(listings)")}
    if "loai_bds" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN loai_bds TEXT DEFAULT 'nha_rieng'")
        conn.execute("UPDATE listings SET loai_bds='nha_rieng' WHERE loai_bds IS NULL")
    if "du_an" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN du_an TEXT")
    if "so_pn" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN so_pn INTEGER")
    # IA v2 Bước 3: cột chuẩn bị scale đa quận
    if "district_id" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN district_id TEXT DEFAULT 'binh_thanh'")
        conn.execute("UPDATE listings SET district_id='binh_thanh' WHERE district_id IS NULL")
    if "ward_id" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN ward_id TEXT")
        conn.execute("UPDATE listings SET ward_id=phuong WHERE ward_id IS NULL")  # backfill = số phường
    if "street_id" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN street_id TEXT")
    # snapshot đa quận
    scols = {r[1] for r in conn.execute("PRAGMA table_info(price_snapshots)")}
    if scols and "district_id" not in scols:
        conn.execute("ALTER TABLE price_snapshots ADD COLUMN district_id TEXT DEFAULT 'binh_thanh'")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


_FIELDS = [
    "source", "loai_bds", "tieu_de", "dia_chi", "quan", "district_id", "ward_id",
    "street_id", "phuong", "loai_duong", "rong_hem", "du_an", "so_pn", "dien_tich",
    "ngang", "dai", "so_tang", "huong", "gia", "gia_per_m2", "ngay_dang",
    "trang_thai", "ghi_chu", "lat", "lng", "url",
]


def insert_many(rows: list[dict]):
    """rows: list dict (đã parse). Bỏ qua key thừa, điền None cho key thiếu."""
    with get_conn() as conn:
        placeholders = ", ".join("?" for _ in _FIELDS)
        cols = ", ".join(_FIELDS)
        conn.executemany(
            f"INSERT INTO listings ({cols}) VALUES ({placeholders})",
            [[r.get(f) for f in _FIELDS] for r in rows],
        )
        return conn.total_changes


def count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]


# ---------------------------------------------------------------------------
# Dự án chung cư sơ cấp (đang/sắp mở bán)
# ---------------------------------------------------------------------------

_PROJECT_FIELDS = ["ten", "trang_thai", "chu_dau_tu", "quan", "district_id",
                   "phuong", "dia_chi", "quy_mo", "gia_info", "mo_ta", "url",
                   "source", "fetched_at"]


def upsert_projects(rows: list[dict]) -> int:
    """Nạp dự án, dedupe theo url (UPSERT). Trả số dòng ghi."""
    with get_conn() as conn:
        cols = ", ".join(_PROJECT_FIELDS)
        ph = ", ".join("?" for _ in _PROJECT_FIELDS)
        upd = ", ".join(f"{c}=excluded.{c}" for c in _PROJECT_FIELDS if c != "url")
        conn.executemany(
            f"INSERT INTO projects ({cols}) VALUES ({ph}) "
            f"ON CONFLICT(url) DO UPDATE SET {upd}",
            [[r.get(f) for f in _PROJECT_FIELDS] for r in rows],
        )
        return conn.total_changes


def list_projects(district_id: str | None = None, statuses: list | None = None,
                  quan: str | None = None):
    """Danh sách dự án, lọc theo trạng thái (mặc định sắp+đang mở bán) và quận."""
    # Mặc định: dự án sơ cấp (chưa bàn giao) — gồm cả 'đang cập nhật' vì batdongsan
    # ít gắn nhãn sắp/đang mở bán cho list HCM (đa số để 'đang cập nhật').
    statuses = statuses or ["sap_mo_ban", "dang_mo_ban", "dang_cap_nhat"]
    where = ["trang_thai IN (%s)" % ",".join("?" for _ in statuses)]
    params: list = list(statuses)
    if quan:
        where.append("quan = ?"); params.append(quan)
    sql = ("SELECT * FROM projects WHERE " + " AND ".join(where) +
           " ORDER BY CASE trang_thai WHEN 'dang_mo_ban' THEN 0 ELSE 1 END, ten")
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def project_quan_list() -> list[str]:
    """Các quận có dự án (cho dropdown lọc)."""
    with get_conn() as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT quan FROM projects WHERE quan IS NOT NULL "
            "AND trang_thai IN ('sap_mo_ban','dang_mo_ban') ORDER BY quan").fetchall()]


def project_status_counts() -> dict:
    with get_conn() as conn:
        return {r[0]: r[1] for r in conn.execute(
            "SELECT trang_thai, COUNT(*) FROM projects GROUP BY trang_thai").fetchall()}


def clear():
    with get_conn() as conn:
        conn.execute("DELETE FROM listings")


# ---------------------------------------------------------------------------
# Truy vấn cho dashboard
# ---------------------------------------------------------------------------

def _where(filters: dict):
    """Dựng mệnh đề WHERE từ filter. Trả về (sql, params)."""
    clauses, params = [], []
    if filters.get("district_id"):
        clauses.append("district_id = ?"); params.append(filters["district_id"])
    if filters.get("loai_bds"):
        clauses.append("loai_bds = ?"); params.append(filters["loai_bds"])
    if filters.get("phuong"):
        clauses.append("phuong = ?"); params.append(str(filters["phuong"]))
    if filters.get("loai_duong"):
        clauses.append("loai_duong = ?"); params.append(filters["loai_duong"])
    if filters.get("gia_min") is not None:
        clauses.append("gia >= ?"); params.append(filters["gia_min"])
    if filters.get("gia_max") is not None:
        clauses.append("gia <= ?"); params.append(filters["gia_max"])
    if filters.get("dt_min") is not None:
        clauses.append("dien_tich >= ?"); params.append(filters["dt_min"])
    if filters.get("dt_max") is not None:
        clauses.append("dien_tich <= ?"); params.append(filters["dt_max"])
    sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return sql, params


def _filt(loai_bds: str | None = None, district_id: str | None = None):
    """Dựng mệnh đề ' AND ...' lọc theo loại + quận (cho các hàm aggregate). Trả (sql, params)."""
    cl, p = [], []
    if district_id:
        cl.append("district_id = ?"); p.append(district_id)
    if loai_bds:
        cl.append("loai_bds = ?"); p.append(loai_bds)
    return ((" AND " + " AND ".join(cl)) if cl else ""), p


def districts_in_db() -> list[str]:
    """Danh sách district_id đang có dữ liệu (cho dropdown chọn quận)."""
    with get_conn() as conn:
        return [r[0] for r in conn.execute(
            "SELECT district_id, COUNT(*) c FROM listings WHERE district_id IS NOT NULL "
            "GROUP BY district_id ORDER BY c DESC").fetchall()]


def list_listings(filters: dict | None = None, limit: int = 500):
    filters = filters or {}
    sql, params = _where(filters)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM listings{sql} ORDER BY gia_per_m2 DESC NULLS LAST LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def avg_price_by_ward(loai_bds: str | None = None, district_id: str | None = None, min_n: int = 5):
    """Giá/m² trung bình theo phường (cho bar chart). Bỏ phường có < min_n tin (nhiễu)."""
    extra, params = _filt(loai_bds, district_id)
    params = params + [min_n]
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT phuong,
                      ROUND(AVG(gia_per_m2), 1) AS avg_gia_m2,
                      COUNT(*) AS n
               FROM listings
               WHERE gia_per_m2 IS NOT NULL AND phuong IS NOT NULL{extra}
               GROUP BY phuong
               HAVING COUNT(*) >= ?""",
            params,
        ).fetchall()
        return sorted((dict(r) for r in rows), key=lambda d: _ward_sort_key(d["phuong"]))


def scatter_data(loai_bds: str | None = None, district_id: str | None = None):
    """Diện tích vs giá (phát hiện outlier)."""
    extra, params = _filt(loai_bds, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT dien_tich, gia, phuong, loai_duong, tieu_de
               FROM listings
               WHERE dien_tich IS NOT NULL AND gia IS NOT NULL{extra}""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def _median(vals):
    return round(median(vals), 1) if vals else None


def stats(loai_bds: str | None = None, district_id: str | None = None):
    """Các chỉ số tổng quan cho KPI cards (dùng trung vị/percentile cho robust với outlier)."""
    f, p = _filt(loai_bds, district_id)
    with get_conn() as conn:
        gia_m2 = [r[0] for r in conn.execute(
            f"SELECT gia_per_m2 FROM listings WHERE gia_per_m2 IS NOT NULL{f}", p).fetchall()]
        gia = sorted(r[0] for r in conn.execute(
            f"SELECT gia FROM listings WHERE gia IS NOT NULL{f}", p).fetchall())
        dt = [r[0] for r in conn.execute(
            f"SELECT dien_tich FROM listings WHERE dien_tich IS NOT NULL{f}", p).fetchall()]
        n_phuong = conn.execute(
            f"SELECT COUNT(DISTINCT phuong) FROM listings WHERE phuong IS NOT NULL{f}", p).fetchone()[0]
        n_real = conn.execute(
            f"SELECT COUNT(*) FROM listings WHERE source='thuc_te'{f}", p).fetchone()[0]
        n_url = conn.execute(
            f"SELECT COUNT(*) FROM listings WHERE url IS NOT NULL{f}", p).fetchone()[0]

    gia_p25 = gia_p75 = None
    if len(gia) >= 4:
        q = quantiles(gia, n=4)
        gia_p25, gia_p75 = round(q[0], 1), round(q[2], 1)

    return {
        "gia_median_m2": _median(gia_m2),
        "dt_median": _median(dt),
        "tong": len(gia_m2),
        "n_phuong": n_phuong,
        "n_real": n_real,
        "gia_p25": gia_p25,
        "gia_p75": gia_p75,
        "is_demo": n_url == 0,  # chưa có data crawl thật (mọi tin đều là mock)
    }


def wards(loai_bds: str | None = None, district_id: str | None = None):
    f, p = _filt(loai_bds, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT phuong FROM listings WHERE phuong IS NOT NULL{f}", p
        ).fetchall()
        return sorted((r[0] for r in rows), key=_ward_sort_key)


def count_by_type(district_id: str | None = None) -> dict:
    """Số tin từng loại BĐS — cho badge trên tab."""
    f, p = _filt(None, district_id)
    where = (" WHERE 1=1" + f) if f else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT loai_bds, COUNT(*) FROM listings{where} GROUP BY loai_bds", p).fetchall()
    return {r[0] or LOAI_BDS_DEFAULT: r[1] for r in rows}


def count_by_source(loai_bds: str | None = None, district_id: str | None = None) -> dict:
    """Số tin theo nguồn site (đối chiếu chéo)."""
    f, p = _filt(loai_bds, district_id)
    where = (" WHERE 1=1" + f) if f else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT source, COUNT(*) FROM listings{where} GROUP BY source", p).fetchall()
    return {r[0]: r[1] for r in rows}


# ---------------------------------------------------------------------------
# So sánh giá theo khu vực (SRS Mục 2 + Mở rộng 1)
# ---------------------------------------------------------------------------

def _ward_sort_key(p: str):
    """Phường số sort theo số; phường tên sort theo chuỗi (đứng sau)."""
    return (0, int(p)) if str(p).isdigit() else (1, str(p))


def compare_by_area(loai_bds: str, dien_tich: float, sai_so: float = 0.1,
                    ngan_sach: float | None = None, min_n: int = 3,
                    district_id: str | None = None):
    """
    SRS Mục 2 — "So sánh giá theo diện tích mục tiêu".
    Với mỗi phường: lấy các tin cùng loại có diện tích trong [dt*(1-sai_so), dt*(1+sai_so)],
    tính median(giá/m²) làm giá chuẩn → giá ước tính = median * dien_tich.
    Nếu có ngan_sach → đánh giá Khớp/Vượt. Trả list đã sort theo giá ước tính tăng dần.
    """
    dien_tich = float(dien_tich)
    lo, hi = dien_tich * (1 - sai_so), dien_tich * (1 + sai_so)
    df, dp = _filt(None, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT phuong, gia_per_m2 FROM listings
               WHERE loai_bds = ? AND phuong IS NOT NULL AND gia_per_m2 IS NOT NULL
                 AND dien_tich BETWEEN ? AND ?{df}""",
            [loai_bds, lo, hi] + dp,
        ).fetchall()

    by_ward: dict[str, list] = {}
    for r in rows:
        by_ward.setdefault(r[0], []).append(r[1])

    out = []
    for phuong, vals in by_ward.items():
        if len(vals) < min_n:
            continue
        med = round(median(vals), 1)
        gia_est = round(med * dien_tich / 1000, 2)  # tỷ
        item = {
            "phuong": phuong,
            "median_m2": med,
            "gia_est": gia_est,
            "n": len(vals),
            "it_mau": len(vals) < 3,  # cảnh báo ít mẫu
        }
        if ngan_sach:
            diff = (gia_est - ngan_sach) / ngan_sach
            if gia_est <= ngan_sach * 1.001:
                item["danh_gia"] = "khop"
                item["danh_gia_pct"] = round(diff * 100)
            else:
                item["danh_gia"] = "vuot"
                item["danh_gia_pct"] = round(diff * 100)
        out.append(item)

    out.sort(key=lambda x: x["gia_est"])
    return out


def search_by_budget(loai_bds: str, ngan_sach: float, min_n: int = 3,
                     district_id: str | None = None):
    """
    SRS Mở rộng 1 — "Tìm kiếm ngược theo ngân sách cố định".
    Với mỗi phường: median(giá/m²) toàn bộ tin cùng loại → diện tích mua được = ngan_sach / median.
    Trả list sort theo diện tích mua được giảm dần (mua được nhiều m² nhất lên đầu).
    """
    ngan_sach = float(ngan_sach)
    df, dp = _filt(None, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT phuong, gia_per_m2 FROM listings
               WHERE loai_bds = ? AND phuong IS NOT NULL AND gia_per_m2 IS NOT NULL{df}""",
            [loai_bds] + dp,
        ).fetchall()

    by_ward: dict[str, list] = {}
    for r in rows:
        by_ward.setdefault(r[0], []).append(r[1])

    out = []
    for phuong, vals in by_ward.items():
        if len(vals) < min_n:
            continue
        med = round(median(vals), 1)
        dt_est = round(ngan_sach * 1000 / med, 1)  # m²
        out.append({
            "phuong": phuong,
            "median_m2": med,
            "dt_est": dt_est,
            "n": len(vals),
            "it_mau": len(vals) < 3,
        })
    out.sort(key=lambda x: x["dt_est"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# So sánh giá giữa các NGUỒN (Batdongsan vs Chợ Tốt vs mogi)
# ---------------------------------------------------------------------------

def source_overall(loai_bds: str, district_id: str | None = None):
    """Median giá/m² theo từng nguồn (toàn quận). Gồm cả mogi (mức quận)."""
    df, dp = _filt(None, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT source, gia_per_m2 FROM listings
               WHERE loai_bds = ? AND gia_per_m2 IS NOT NULL{df}""",
            [loai_bds] + dp,
        ).fetchall()
    g: dict[str, list] = {}
    for r in rows:
        g.setdefault(r[0], []).append(r[1])
    return {s: {"median_m2": round(median(v), 1), "n": len(v)} for s, v in g.items()}


def source_by_ward(loai_bds: str, district_id: str | None = None, min_n: int = 2):
    """
    Median giá/m² theo (phường × nguồn) — để soi nguồn nào kê giá cao theo từng phường.
    Chỉ gồm nguồn CÓ phường (batdongsan, chotot); mogi phuong=null nên tự loại.
    Trả list {phuong, src: {source: {median_m2, n}}, chenh_pct} sort theo phường.
    """
    df, dp = _filt(None, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT phuong, source, gia_per_m2 FROM listings
               WHERE loai_bds = ? AND phuong IS NOT NULL AND gia_per_m2 IS NOT NULL{df}""",
            [loai_bds] + dp,
        ).fetchall()
    g: dict[str, dict] = {}
    for r in rows:
        g.setdefault(r[0], {}).setdefault(r[1], []).append(r[2])

    out = []
    for ph, srcmap in g.items():
        src = {s: {"median_m2": round(median(v), 1), "n": len(v)}
               for s, v in srcmap.items() if len(v) >= min_n}
        if len(src) < 2:        # cần ≥2 nguồn mới so sánh được
            continue
        meds = [d["median_m2"] for d in src.values()]
        chenh = round((max(meds) - min(meds)) / min(meds) * 100) if min(meds) else 0
        out.append({"phuong": ph, "src": src, "chenh_pct": chenh})
    out.sort(key=lambda x: _ward_sort_key(x["phuong"]))
    return out


# ---------------------------------------------------------------------------
# Gom cụm tin trùng / môi giới kê giá (SRS Mở rộng 2)
# ---------------------------------------------------------------------------

def duplicate_clusters(loai_bds: str, min_size: int = 2, limit: int = 100,
                       district_id: str | None = None):
    """
    Gom các tin nghi là CÙNG 1 BĐS được nhiều môi giới rao (gây nhiễu scatter).
    Khóa gom theo loại:
      - nhà/đất: (phường, diện tích làm tròn, số tầng, loại đường)
      - chung cư: (phường, dự án, số PN, diện tích làm tròn)
    Chỉ giữ cụm có ≥ min_size tin. Mỗi cụm trả biên độ giá min–max + trung vị.
    """
    df, dp = _filt(None, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT phuong, du_an, so_pn, dien_tich, so_tang, loai_duong,
                      gia, gia_per_m2, tieu_de, url
               FROM listings
               WHERE loai_bds = ? AND dien_tich IS NOT NULL AND gia IS NOT NULL
                 AND phuong IS NOT NULL{df}""",
            [loai_bds] + dp,
        ).fetchall()

    groups: dict[tuple, list] = {}
    for r in rows:
        d = dict(r)
        dt_key = round(d["dien_tich"])  # gộp DT chênh lệch nhỏ (59 ~ 59.4)
        if loai_bds == "chung_cu":
            key = (d["phuong"], d["du_an"], d["so_pn"], dt_key)
        else:
            key = (d["phuong"], dt_key, d["so_tang"], d["loai_duong"])
        groups.setdefault(key, []).append(d)

    clusters = []
    for key, items in groups.items():
        if len(items) < min_size:
            continue
        gias = sorted(i["gia"] for i in items)
        clusters.append({
            "phuong": key[0],
            "dien_tich": items[0]["dien_tich"],
            "du_an": items[0].get("du_an"),
            "so_pn": items[0].get("so_pn"),
            "so_tang": items[0].get("so_tang"),
            "loai_duong": items[0].get("loai_duong"),
            "n": len(items),
            "gia_min": round(gias[0], 2),
            "gia_max": round(gias[-1], 2),
            "gia_median": round(median(gias), 2),
            "bien_do": round(gias[-1] - gias[0], 2),  # chênh lệch sàn–trần
            "tin": sorted(items, key=lambda x: x["gia"]),
        })

    # Cụm nhiều tin + biên độ lớn lên đầu (đáng nghi nhất)
    clusters.sort(key=lambda c: (c["n"], c["bien_do"]), reverse=True)
    return clusters[:limit]


# ---------------------------------------------------------------------------
# Tool định giá — comp method
# ---------------------------------------------------------------------------

def dinh_gia(phuong: str, dien_tich: float, loai_duong: str | None = None,
             loai_bds: str | None = None, dt_tolerance: float = 0.2,
             district_id: str | None = None):
    """
    Định giá theo căn tương đồng: cùng loại BĐS + cùng phường (+ cùng loại đường nếu có)
    + diện tích ±tolerance. Trả về P25/P50/P75 của giá/m² và giá ước tính.
    """
    dien_tich = float(dien_tich) if dien_tich not in (None, "") else None
    loai_duong = loai_duong or None
    loai_bds = loai_bds or None

    sql = ("SELECT gia_per_m2 FROM listings "
           "WHERE phuong = ? AND gia_per_m2 IS NOT NULL")
    params = [str(phuong)]
    if district_id:
        sql += " AND district_id = ?"; params.append(district_id)
    if loai_bds:
        sql += " AND loai_bds = ?"; params.append(loai_bds)
    if loai_duong:
        sql += " AND loai_duong = ?"; params.append(loai_duong)
    if dien_tich:
        sql += " AND dien_tich BETWEEN ? AND ?"
        params += [dien_tich * (1 - dt_tolerance), dien_tich * (1 + dt_tolerance)]

    with get_conn() as conn:
        vals = [r[0] for r in conn.execute(sql, params).fetchall()]

    # Nới điều kiện nếu quá ít mẫu: bỏ ràng buộc diện tích
    relaxed = False
    if len(vals) < 3 and dien_tich:
        sql2 = ("SELECT gia_per_m2 FROM listings "
                "WHERE phuong = ? AND gia_per_m2 IS NOT NULL")
        p2 = [str(phuong)]
        if district_id:
            sql2 += " AND district_id = ?"; p2.append(district_id)
        if loai_bds:
            sql2 += " AND loai_bds = ?"; p2.append(loai_bds)
        if loai_duong:
            sql2 += " AND loai_duong = ?"; p2.append(loai_duong)
        with get_conn() as conn:
            vals = [r[0] for r in conn.execute(sql2, p2).fetchall()]
        relaxed = True

    if not vals:
        return {"n": 0, "message": "Không đủ dữ liệu tương đồng để định giá."}

    vals.sort()
    if len(vals) >= 4:
        q = quantiles(vals, n=4)  # [P25, P50, P75]
        p25, p50, p75 = q[0], q[1], q[2]
    else:
        p25 = vals[0]; p50 = median(vals); p75 = vals[-1]

    result = {
        "n": len(vals),
        "relaxed": relaxed,
        "p25_per_m2": round(p25, 1),
        "p50_per_m2": round(p50, 1),
        "p75_per_m2": round(p75, 1),
    }
    if dien_tich:
        result.update({
            "gia_p25": round(p25 * dien_tich / 1000, 3),  # tỷ
            "gia_p50": round(p50 * dien_tich / 1000, 3),
            "gia_p75": round(p75 * dien_tich / 1000, 3),
        })
    return result


# ---------------------------------------------------------------------------
# Heatmap theo phường (SRS Mở rộng 3) — dùng centroid phường, vẽ bubble Chart.js
# ---------------------------------------------------------------------------

def heatmap_data(loai_bds: str, min_n: int = 3, district_id: str | None = None):
    """
    Median giá/m² theo phường + toạ độ centroid → cho bubble map.
    Trả list {phuong, lat, lng, median_m2, n}. Bỏ phường < min_n hoặc không có toạ độ.
    LƯU Ý: geo.py mới có centroid Bình Thạnh → quận khác sẽ rỗng (chờ bản đồ SVG ở backlog).
    """
    from geo import centroid
    df, dp = _filt(None, district_id)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT phuong, gia_per_m2 FROM listings
               WHERE loai_bds = ? AND phuong IS NOT NULL AND gia_per_m2 IS NOT NULL{df}""",
            [loai_bds] + dp,
        ).fetchall()

    by_ward: dict[str, list] = {}
    for r in rows:
        by_ward.setdefault(r[0], []).append(r[1])

    out = []
    for phuong, vals in by_ward.items():
        if len(vals) < min_n:
            continue
        c = centroid(phuong)
        if not c:
            continue
        out.append({
            "phuong": phuong,
            "lat": c[0],
            "lng": c[1],
            "median_m2": round(median(vals), 1),
            "n": len(vals),
        })
    out.sort(key=_ward_sort_key_item)
    return out


def _ward_sort_key_item(item):
    return _ward_sort_key(item["phuong"])


# ---------------------------------------------------------------------------
# Lịch sử & xu hướng giá (SRS Mở rộng 4)
# ---------------------------------------------------------------------------

def record_snapshot(ngay: str | None = None, source: str = "real", min_n: int = 3):
    """
    Chụp median giá/m² hiện tại theo (loai_bds, phường) và ghi vào price_snapshots.
    Gọi định kỳ (cron/tay) để tích luỹ lịch sử. Trả số dòng đã ghi.
    """
    import datetime
    ngay = ngay or datetime.date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT district_id, loai_bds, phuong, gia_per_m2 FROM listings
               WHERE gia_per_m2 IS NOT NULL AND phuong IS NOT NULL AND loai_bds IS NOT NULL"""
        ).fetchall()

        groups: dict[tuple, list] = {}
        for r in rows:
            groups.setdefault((r[0], r[1], r[2]), []).append(r[3])

        batch = []
        for (dist, lb, ph), vals in groups.items():
            if len(vals) < min_n:
                continue
            batch.append((ngay, dist, lb, ph, round(median(vals), 1), len(vals), source))

        # Tránh ghi trùng cùng ngày + cùng source
        conn.execute("DELETE FROM price_snapshots WHERE ngay = ? AND source = ?", (ngay, source))
        conn.executemany(
            "INSERT INTO price_snapshots (ngay, district_id, loai_bds, phuong, median_m2, n, source) "
            "VALUES (?,?,?,?,?,?,?)", batch)
        return len(batch)


def snapshot_dates():
    with get_conn() as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT ngay FROM price_snapshots ORDER BY ngay").fetchall()]


def snapshot_has_demo() -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM price_snapshots WHERE source='demo' LIMIT 1").fetchone() is not None


def trend_data(loai_bds: str, district_id: str | None = None):
    """
    Xu hướng giá/m² theo thời gian cho 1 loại BĐS (+ quận nếu chỉ định).
    Trả {dates, overall (median toàn quận mỗi mốc), wards: {phuong: [median theo dates]}}.
    """
    extra = " AND district_id = ?" if district_id else ""
    p = [loai_bds] + ([district_id] if district_id else [])
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT ngay, phuong, median_m2 FROM price_snapshots
               WHERE loai_bds = ?{extra} ORDER BY ngay""",
            p,
        ).fetchall()

    dates = sorted({r[0] for r in rows})
    by_ward: dict[str, dict] = {}
    by_date_vals: dict[str, list] = {}
    for r in rows:
        by_ward.setdefault(r[1], {})[r[0]] = r[2]
        by_date_vals.setdefault(r[0], []).append(r[2])

    overall = [round(median(by_date_vals[d]), 1) if by_date_vals.get(d) else None for d in dates]
    wards = {}
    for ph, dmap in by_ward.items():
        wards[ph] = [dmap.get(d) for d in dates]

    # % thay đổi giá tổng từ mốc đầu → mốc cuối
    pct = None
    if len(overall) >= 2 and overall[0] and overall[-1]:
        pct = round((overall[-1] - overall[0]) / overall[0] * 100, 1)

    return {"dates": dates, "overall": overall, "wards": wards, "pct": pct}


if __name__ == "__main__":
    init_db()
    print("DB ready at", os.path.abspath(DB_PATH), "| rows:", count())
