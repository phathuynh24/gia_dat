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

from flask import Flask, render_template, request
import db
from db import LOAI_DUONG_LABEL

app = Flask(__name__)


def _f(name):
    """Đọc số từ query, trả None nếu rỗng."""
    v = request.args.get(name, "").strip()
    try:
        return float(v) if v else None
    except ValueError:
        return None


@app.route("/")
def dashboard():
    filters = {
        "phuong": request.args.get("phuong") or None,
        "loai_duong": request.args.get("loai_duong") or None,
        "gia_min": _f("gia_min"), "gia_max": _f("gia_max"),
        "dt_min": _f("dt_min"), "dt_max": _f("dt_max"),
    }
    listings = db.list_listings(filters)
    return render_template(
        "dashboard.html",
        listings=listings,
        total=db.count(),
        stats=db.stats(),
        wards=db.wards(),
        loai_label=LOAI_DUONG_LABEL,
        filters=filters,
        bar_data=json.dumps(db.avg_price_by_ward()),
        scatter_data=json.dumps(db.scatter_data()),
    )


@app.route("/dinh-gia")
def dinh_gia():
    phuong = request.args.get("phuong") or None
    dien_tich = request.args.get("dien_tich") or None
    loai_duong = request.args.get("loai_duong") or None

    result = None
    if phuong and dien_tich:
        result = db.dinh_gia(phuong, dien_tich, loai_duong)

    return render_template(
        "dinh_gia.html",
        wards=db.wards(),
        loai_label=LOAI_DUONG_LABEL,
        result=result,
        sel={"phuong": phuong, "dien_tich": dien_tich, "loai_duong": loai_duong},
    )


if __name__ == "__main__":
    db.init_db()
    if db.count() == 0:
        print("DB trống — chạy 'python src/seed.py' để nạp dữ liệu mẫu.")
    app.run(debug=True, use_reloader=False, port=5000)
