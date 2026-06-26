"""
Web app dashboard giá nhà Bình Thạnh (Flask).

Chạy:  python src/app.py   ->  http://127.0.0.1:5000

Trang:
  /            Dashboard: giá/m² theo phường, scatter DT-giá, bảng tin có filter
  /dinh-gia    Tool định giá nhanh (comp method, P25/P50/P75)
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

# Windows console mặc định cp1252 -> ép UTF-8 để log tiếng Việt không lỗi
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from flask import Flask, render_template, request, session
import db
from db import LOAI_DUONG_LABEL, LOAI_BDS_LABEL, LOAI_BDS_DEFAULT, SOURCE_LABEL
from districts import DISTRICTS, LABEL as DISTRICT_LABEL

app = Flask(__name__)
# Secret key: lấy từ env khi deploy, fallback local. Chỉ dùng lưu lựa chọn quận trong session.
app.secret_key = os.environ.get("SECRET_KEY", "gia-dat-local-mvp")

# Tạo bảng/migrate khi import (để gunicorn trên server cũng khởi tạo DB, không chỉ khi chạy local).
db.init_db()

DISTRICT_DEFAULT = "binh_thanh"


def _loai_bds():
    """Tab loại BĐS đang chọn (mặc định nhà riêng). Bỏ qua giá trị lạ."""
    v = request.args.get("loai_bds") or LOAI_BDS_DEFAULT
    return v if v in LOAI_BDS_LABEL else LOAI_BDS_DEFAULT


def _district():
    """Quận đang chọn — sticky qua session để giữ khi chuyển tab.
    Mặc định Bình Thạnh (giữ nguyên hành vi cũ)."""
    v = request.args.get("quan")
    if v and v in DISTRICTS:
        session["quan"] = v
        return v
    return session.get("quan", DISTRICT_DEFAULT)


@app.template_filter("wardlabel")
def _wardlabel(w):
    """Phường số → 'P22'; phường chữ → giữ nguyên tên ('Phú Mỹ')."""
    if w is None or w == "":
        return "—"
    return f"P{w}" if str(w).isdigit() else str(w)


@app.context_processor
def _inject_district():
    """Cấp dữ liệu cho dropdown chọn quận ở header (mọi trang)."""
    avail = db.districts_in_db() or [DISTRICT_DEFAULT]
    return dict(cur_district=_district(), district_label=DISTRICT_LABEL,
                districts_avail=avail)


def _f(name):
    """Đọc số từ query, trả None nếu rỗng."""
    v = request.args.get(name, "").strip()
    try:
        return float(v) if v else None
    except ValueError:
        return None


@app.route("/")
def dashboard():
    loai_bds = _loai_bds()
    d = _district()
    filters = {
        "loai_bds": loai_bds,
        "district_id": d,
        "phuong": request.args.get("phuong") or None,
        "loai_duong": request.args.get("loai_duong") or None,
        "gia_min": _f("gia_min"), "gia_max": _f("gia_max"),
        "dt_min": _f("dt_min"), "dt_max": _f("dt_max"),
    }
    listings = db.list_listings(filters)
    counts = db.count_by_type(d)
    bar = db.avg_price_by_ward(loai_bds, d)
    return render_template(
        "dashboard.html",
        listings=listings,
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        counts=counts,
        total=sum(counts.values()),
        stats=db.stats(loai_bds, d),
        wards=db.wards(loai_bds, d),
        loai_label=LOAI_DUONG_LABEL,
        source_label=SOURCE_LABEL,
        source_counts=db.count_by_source(loai_bds, d),
        filters=filters,
        has_ward_chart=len(bar) > 0,   # ẩn chart theo phường nếu không đủ data
        bar_data=json.dumps(bar),
        scatter_data=json.dumps(db.scatter_data(loai_bds, d)),
    )


@app.route("/dinh-gia")
def dinh_gia():
    loai_bds = _loai_bds()
    d = _district()
    phuong = request.args.get("phuong") or None
    dien_tich = request.args.get("dien_tich") or None
    loai_duong = request.args.get("loai_duong") or None

    result = None
    if phuong and dien_tich:
        result = db.dinh_gia(phuong, dien_tich, loai_duong, loai_bds, district_id=d)

    return render_template(
        "dinh_gia.html",
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        wards=db.wards(loai_bds, d),
        loai_label=LOAI_DUONG_LABEL,
        result=result,
        sel={"phuong": phuong, "dien_tich": dien_tich,
             "loai_duong": loai_duong, "loai_bds": loai_bds},
    )


@app.route("/so-sanh")
def so_sanh():
    """SRS Mục 2 (theo diện tích) + Mở rộng 1 (theo ngân sách)."""
    loai_bds = _loai_bds()
    mode = request.args.get("mode") or "dien_tich"
    if mode not in ("dien_tich", "ngan_sach"):
        mode = "dien_tich"
    dien_tich = _f("dien_tich")
    ngan_sach = _f("ngan_sach")
    try:
        sai_so = float(request.args.get("sai_so") or 0.1)
    except ValueError:
        sai_so = 0.1

    d = _district()
    rows = None
    if mode == "dien_tich" and dien_tich:
        rows = db.compare_by_area(loai_bds, dien_tich, sai_so, ngan_sach, district_id=d)
    elif mode == "ngan_sach" and ngan_sach:
        rows = db.search_by_budget(loai_bds, ngan_sach, district_id=d)

    return render_template(
        "so_sanh.html",
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        mode=mode,
        rows=rows,
        sel={"dien_tich": dien_tich, "ngan_sach": ngan_sach, "sai_so": sai_so},
    )


@app.route("/so-nguon")
def so_nguon():
    """So sánh giá giữa các nguồn (Batdongsan vs Chợ Tốt vs mogi) — toàn quận + theo phường."""
    loai_bds = _loai_bds()
    d = _district()
    return render_template(
        "so_nguon.html",
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        source_label=SOURCE_LABEL,
        overall=db.source_overall(loai_bds, d),
        by_ward=db.source_by_ward(loai_bds, d),
    )


@app.route("/trung-lap")
def trung_lap():
    """SRS Mở rộng 2 — gom cụm tin trùng / môi giới kê giá."""
    loai_bds = _loai_bds()
    clusters = db.duplicate_clusters(loai_bds, district_id=_district())
    return render_template(
        "trung_lap.html",
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        loai_label=LOAI_DUONG_LABEL,
        clusters=clusters,
    )


@app.route("/vay-von")
def vay_von():
    """Tính vay vốn: vốn tự có tối thiểu, trả góp hàng tháng, lãi theo thời gian."""
    from finance import loan_breakdown
    gia = _f("gia")
    try:
        ty_le_vay = float(request.args.get("ty_le_vay") or 70) / 100
        lai_suat = float(request.args.get("lai_suat") or 10)
        nam = int(float(request.args.get("nam") or 20))
    except ValueError:
        ty_le_vay, lai_suat, nam = 0.7, 10.0, 20

    result = loan_breakdown(gia, ty_le_vay, lai_suat, nam) if gia else None
    return render_template(
        "vay_von.html",
        result=result,
        sel={"gia": gia, "ty_le_vay": round(ty_le_vay * 100),
             "lai_suat": lai_suat, "nam": nam},
    )


@app.route("/heatmap")
def heatmap():
    """SRS Mở rộng 3 — bản đồ nhiệt giá theo phường (bubble map, centroid phường)."""
    loai_bds = _loai_bds()
    points = db.heatmap_data(loai_bds, district_id=_district())
    return render_template(
        "heatmap.html",
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        points=json.dumps(points),
        n_points=len(points),
    )


@app.route("/xu-huong")
def xu_huong():
    """SRS Mở rộng 4 — lịch sử & xu hướng giá theo thời gian."""
    loai_bds = _loai_bds()
    trend = db.trend_data(loai_bds, district_id=_district())
    return render_template(
        "xu_huong.html",
        loai_bds=loai_bds,
        loai_bds_label=LOAI_BDS_LABEL,
        trend=json.dumps(trend),
        n_dates=len(trend["dates"]),
        pct=trend["pct"],
        has_demo=db.snapshot_has_demo(),
    )


if __name__ == "__main__":
    if db.count() == 0:
        print("DB trống — chạy 'python src/seed.py' để nạp dữ liệu mẫu.")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
