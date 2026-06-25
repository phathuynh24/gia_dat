"""
Lớp dữ liệu: SQLite làm database (đủ dùng cho <5,000 bản ghi như plan MVP).

Schema bám theo plan: địa chỉ, phường, loại đường, rộng hẻm, diện tích, số tầng,
hướng, giá rao, ngày đăng, trạng thái, ghi chú, lat/lng, giá/m² (tính sẵn).
"""

import os
import sqlite3
from statistics import quantiles, median

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "listings.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    DEFAULT 'crawl',   -- 'crawl' | 'thuc_te' (giá đóng thật)
    tieu_de     TEXT,
    dia_chi     TEXT,
    quan        TEXT    DEFAULT 'Bình Thạnh',
    phuong      TEXT,
    loai_duong  TEXT,                       -- 'mat_tien' | 'hxh' | 'hem'
    rong_hem    REAL,
    dien_tich   REAL,                       -- m2
    ngang       REAL,
    dai         REAL,
    so_tang     INTEGER,
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
"""

LOAI_DUONG_LABEL = {
    "mat_tien": "Mặt tiền",
    "hxh": "Hẻm xe hơi",
    "hem": "Hẻm",
}


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


_FIELDS = [
    "source", "tieu_de", "dia_chi", "quan", "phuong", "loai_duong", "rong_hem",
    "dien_tich", "ngang", "dai", "so_tang", "huong", "gia", "gia_per_m2",
    "ngay_dang", "trang_thai", "ghi_chu", "lat", "lng", "url",
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


def clear():
    with get_conn() as conn:
        conn.execute("DELETE FROM listings")


# ---------------------------------------------------------------------------
# Truy vấn cho dashboard
# ---------------------------------------------------------------------------

def _where(filters: dict):
    """Dựng mệnh đề WHERE từ filter. Trả về (sql, params)."""
    clauses, params = [], []
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


def list_listings(filters: dict | None = None, limit: int = 500):
    filters = filters or {}
    sql, params = _where(filters)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM listings{sql} ORDER BY gia_per_m2 DESC NULLS LAST LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def avg_price_by_ward(min_n: int = 5):
    """Giá/m² trung bình theo phường (cho bar chart). Bỏ phường có < min_n tin (nhiễu)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT phuong,
                      ROUND(AVG(gia_per_m2), 1) AS avg_gia_m2,
                      COUNT(*) AS n
               FROM listings
               WHERE gia_per_m2 IS NOT NULL AND phuong IS NOT NULL
               GROUP BY phuong
               HAVING COUNT(*) >= ?
               ORDER BY CAST(phuong AS INTEGER)""",
            (min_n,),
        ).fetchall()
        return [dict(r) for r in rows]


def scatter_data():
    """Diện tích vs giá (phát hiện outlier)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT dien_tich, gia, phuong, loai_duong, tieu_de
               FROM listings
               WHERE dien_tich IS NOT NULL AND gia IS NOT NULL"""
        ).fetchall()
        return [dict(r) for r in rows]


def _median(vals):
    return round(median(vals), 1) if vals else None


def stats():
    """Các chỉ số tổng quan cho KPI cards (dùng trung vị/percentile cho robust với outlier)."""
    with get_conn() as conn:
        gia_m2 = [r[0] for r in conn.execute(
            "SELECT gia_per_m2 FROM listings WHERE gia_per_m2 IS NOT NULL").fetchall()]
        gia = sorted(r[0] for r in conn.execute(
            "SELECT gia FROM listings WHERE gia IS NOT NULL").fetchall())
        dt = [r[0] for r in conn.execute(
            "SELECT dien_tich FROM listings WHERE dien_tich IS NOT NULL").fetchall()]
        n_phuong = conn.execute(
            "SELECT COUNT(DISTINCT phuong) FROM listings WHERE phuong IS NOT NULL").fetchone()[0]
        n_real = conn.execute(
            "SELECT COUNT(*) FROM listings WHERE source='thuc_te'").fetchone()[0]
        n_url = conn.execute(
            "SELECT COUNT(*) FROM listings WHERE url IS NOT NULL").fetchone()[0]

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


def wards():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT phuong FROM listings WHERE phuong IS NOT NULL "
            "ORDER BY CAST(phuong AS INTEGER)"
        ).fetchall()
        return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Tool định giá — comp method
# ---------------------------------------------------------------------------

def dinh_gia(phuong: str, dien_tich: float, loai_duong: str | None = None,
             dt_tolerance: float = 0.2):
    """
    Định giá theo căn tương đồng: cùng phường (+ cùng loại đường nếu có)
    + diện tích ±tolerance. Trả về P25/P50/P75 của giá/m² và giá ước tính.
    """
    dien_tich = float(dien_tich) if dien_tich not in (None, "") else None
    loai_duong = loai_duong or None

    sql = ("SELECT gia_per_m2 FROM listings "
           "WHERE phuong = ? AND gia_per_m2 IS NOT NULL")
    params = [str(phuong)]
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


if __name__ == "__main__":
    init_db()
    print("DB ready at", os.path.abspath(DB_PATH), "| rows:", count())
