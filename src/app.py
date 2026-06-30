"""
Web app dashboard giá nhà Bình Thạnh (Flask).

Chạy:  python src/app.py   ->  http://127.0.0.1:5000

Trang:
  /            Dashboard: giá/m² theo phường, scatter DT-giá, bảng tin có filter
  /dinh-gia    Tool định giá nhanh (comp method, P25/P50/P75)
"""

import sys, os, json, re, html
sys.path.insert(0, os.path.dirname(__file__))

# Windows console mặc định cp1252 -> ép UTF-8 để log tiếng Việt không lỗi
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from flask import Flask, render_template, request, session, redirect, url_for
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
    """Loại BĐS đang chọn — sticky qua session để ĐỒNG BỘ giữa mọi tab.
    Chọn ở tab nào thì các tab khác giữ nguyên loại đó. Mặc định chung cư."""
    v = request.args.get("loai_bds")
    if v and v in LOAI_BDS_LABEL:
        session["loai_bds"] = v
        return v
    return session.get("loai_bds", LOAI_BDS_DEFAULT)


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


def _street_from_url(url):
    """batdongsan nhúng tên đường trong slug: '...-duong-<đường>-phuong-<n>-...'."""
    if not url:
        return None
    m = re.search(r"-(?:duong|pho)-([a-z0-9-]+?)-phuong-", url)
    if m:
        return m.group(1).replace("-", " ").strip() or None
    return None


def _project_from_url(url):
    """Tên dự án chung cư nằm sau '-phuong-<n>-' trong slug batdongsan."""
    if not url:
        return None
    m = re.search(r"-phuong-\d+[a-z]?-([a-z][a-z0-9-]+?)/", url)
    if m:
        proj = m.group(1).replace("-", " ").strip()
        # bỏ hậu tố mã loại tin (vd '66') — chỉ nhận khi có chữ cái
        return proj if re.search(r"[a-z]", proj) and len(proj) > 3 else None
    return None


def _project_from_title(title):
    """Tên dự án chung cư trong tiêu đề mogi/chotot: thường sau 'tại'/'dự án'
    (vd 'căn hộ 2PN tại The Infiniti – Riviera Point' → 'The Infiniti')."""
    if not title:
        return None
    m = re.search(r"tại\s+", title, re.IGNORECASE) \
        or re.search(r"dự\s*án\s+", title, re.IGNORECASE)
    if not m:
        return None
    out = []
    for w in re.split(r"\s+", title[m.end():]):
        wc = w.strip(".,-/()–")
        if not wc:
            if out:
                break
            continue
        if wc[0].isdigit():
            break
        if wc[0].isupper():
            out.append(wc)
            if len(out) >= 3:
                break
        elif out:
            break
    name = " ".join(out).strip()
    return name if len(name) >= 3 else None


def _street_from_title(title):
    """Trích tên đường từ tiêu đề chotot/mogi: sau 'mặt tiền'/'MT'/'đường' → các từ Hoa liền nhau.
    Dừng khi gặp số, dấu phẩy, hoặc từ viết thường (vd 'Phan Văn Hân 40.3m' → 'Phan Văn Hân')."""
    if not title:
        return None
    # 'đường' đứng ngay trước tên đường nên ưu tiên; nếu không có mới tới 'mặt tiền'/'MT'
    # (tránh dính số tầng kiểu 'Mặt Tiền 4Lầu Đường ...').
    m = re.search(r"đường\s+", title, re.IGNORECASE) \
        or re.search(r"(?:mặt\s*tiền|\bmt\b)\s+", title, re.IGNORECASE)
    if not m:
        return None
    rest = re.sub(r"^(?:đường)\s+", "", title[m.end():], flags=re.IGNORECASE)
    out = []
    for w in re.split(r"[\s,]+", rest):
        wc = w.strip(".,-/")
        if not wc or any(c.isdigit() for c in wc):
            break
        if wc[0].isupper():           # .isupper() xử lý đúng chữ Hoa tiếng Việt (Đ, À-Ỹ)
            out.append(wc)
            if len(out) >= 4:
                break
        else:
            break
    name = " ".join(out).strip()
    return name if len(name) >= 3 else None


@app.template_filter("decodehtml")
def _decodehtml(s):
    """Giải mã ký tự HTML trong tiêu đề (mogi trả '&#127882;', '&#8211;' …)."""
    return html.unescape(s) if s else s


@app.template_filter("mapquery")
def _mapquery(l):
    """Dựng chuỗi địa chỉ CỤ THỂ để Google Maps thả ghim đúng vị trí (không cần API key/toạ độ).

    Dữ liệu rao chỉ có tới phường → query mức phường chỉ canh giữa khu, KHÔNG có ghim.
    Nên trích thêm tên ĐƯỜNG (URL batdongsan / tiêu đề chotot) hoặc DỰ ÁN (chung cư) để
    Google định vị tới điểm cụ thể. Luôn gắn đuôi quận + TP để không nhầm tỉnh khác.
    """
    quan = (l.get("quan") or "Bình Thạnh").strip()
    phuong = l.get("phuong")
    title = html.unescape(l.get("tieu_de") or "")  # mogi/chotot có ký tự HTML (&#127882; …)

    place = None  # phần cụ thể nhất: dự án (chung cư) hoặc tên đường
    if l.get("loai_bds") == "chung_cu":
        place = (l.get("du_an") or "").strip() or _project_from_url(l.get("url")) \
            or _project_from_title(title)
    if not place:
        place = _street_from_url(l.get("url")) or _street_from_title(title)

    parts = []
    if place:
        parts.append(place)
    if phuong:
        parts.append(f"Phường {phuong}" if str(phuong).isdigit() else str(phuong))
    parts.append(quan)
    parts.append("TP Hồ Chí Minh")
    return ", ".join(parts)


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

    # Các mục "khảo sát thị trường" gộp thẳng vào Tổng quan (trước là /heatmap, /xu-huong, /so-nguon)
    heat_points = db.heatmap_data(loai_bds, district_id=d)
    trend = db.trend_data(loai_bds, district_id=d)
    src_overall = db.source_overall(loai_bds, d)
    src_by_ward = db.source_by_ward(loai_bds, d)
    # Teaser "Săn hàng ngộp": chỉ cần SỐ cụm nghi trùng (không bê cả bảng vào)
    n_clusters = len(db.duplicate_clusters(loai_bds, district_id=d))

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
        # --- Gộp khảo sát thị trường ---
        heat_points=json.dumps(heat_points),
        n_heat=len(heat_points),
        trend=json.dumps(trend),
        n_dates=len(trend["dates"]),
        trend_pct=trend["pct"],
        has_demo=db.snapshot_has_demo(),
        src_overall=src_overall,
        src_by_ward=src_by_ward,
        n_clusters=n_clusters,
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
    """Tính vay vốn + thẩm định khả năng vay theo lãi suất THẬT của ngân hàng.

    Chọn ngân hàng (mặc định BIDV) → auto lấy lãi ưu đãi/thả nổi + LTV + DTI.
    Chọn 'tu_nhap' để tự nhập lãi cố định (tính case khác). Nhập thu nhập để thẩm định.
    """
    from finance import loan_breakdown, appraise_loan, compare_banks
    import bank_rates

    rates = bank_rates.load()
    banks = rates["banks"]
    bank_key = request.args.get("bank") or bank_rates.DEFAULT_BANK
    if bank_key not in banks and bank_key != "tu_nhap":
        bank_key = bank_rates.DEFAULT_BANK

    gia = _f("gia")
    thu_nhap = _f("thu_nhap")
    try:
        ty_le_vay = float(request.args.get("ty_le_vay") or 70) / 100
        nam = int(float(request.args.get("nam") or 20))
    except ValueError:
        ty_le_vay, nam = 0.7, 20

    result = appraise = None
    bank = banks.get(bank_key)
    if bank_key == "tu_nhap":
        # Tự nhập: lãi cố định 1 giai đoạn
        try:
            lai_suat = float(request.args.get("lai_suat") or 10)
        except ValueError:
            lai_suat = 10.0
        if gia:
            result = loan_breakdown(gia, ty_le_vay, lai_suat, nam)
            # Thẩm định với LTV/DTI mặc định + lãi tự nhập làm "thả nổi"
            appraise = appraise_loan(
                gia, thu_nhap,
                {"ten": "Tự nhập", "ltv_max": 1.0, "dti_max": 0.6, "lai_tha_noi": lai_suat},
                ty_le_vay, nam) if (gia and thu_nhap) else None
        sel_lai = lai_suat
    else:
        # Theo ngân hàng: lãi 2 giai đoạn + LTV/DTI của bank
        if gia:
            result = loan_breakdown(
                gia, ty_le_vay, bank["lai_tha_noi"], nam,
                lai_uu_dai=bank["lai_uu_dai"], uu_dai_thang=bank["uu_dai_thang"],
                lai_tha_noi=bank["lai_tha_noi"])
            if thu_nhap:
                appraise = appraise_loan(gia, thu_nhap, bank, ty_le_vay, nam)
        sel_lai = bank["lai_tha_noi"] if bank else 10.0

    # Bảng so sánh & xếp hạng tất cả ngân hàng cho đúng tình huống user nhập
    compare = compare_banks(gia, thu_nhap, ty_le_vay, nam, banks) if gia else None

    # Vài số liệu "kịch bản" để kể chuyện cho người mua lần đầu (tránh để template tính)
    story = None
    if result:
        jump = (result["tra_thang_tha_noi"] - result["tra_thang_uu_dai"]) \
            if result.get("hai_gd") else 0
        story = {
            "jump": round(jump, 1),
            "jump_pct": round(jump / result["tra_thang_uu_dai"] * 100) if result.get("hai_gd") and result["tra_thang_uu_dai"] else 0,
            "lai_vs_gia_pct": round(result["tong_lai"] / result["gia"] * 100) if result["gia"] else 0,
            "tong_tra_ratio": round(result["tong_tra"] / result["gia"], 2) if result["gia"] else 0,
        }

    # Nguồn + thời điểm lấy data TỪNG chỉ số của bank đang chọn (hiển thị minh bạch lên UI)
    field_sources = None
    if bank and bank_key != "tu_nhap":
        d_fetch = rates.get("fetched_at") or "?"
        d_topi = rates.get("topi_date")
        promo_src = (bank.get("nguon_uu_dai") or bank.get("nguon")
                     or "tham khảo nội bộ (chưa có nguồn)")
        flt_src = (f"webgia.com — lãi tiền gửi {bank.get('ls_ky_han','')} {bank.get('ls_tham_chieu','')}% "
                   f"+ biên độ {bank.get('bien_do')}% · cào {d_fetch}") if bank.get("lai_real") \
            else "tham khảo nội bộ (chưa cào được lãi thả nổi)"
        co_uu_dai = bank["lai_uu_dai"] < bank["lai_tha_noi"]
        field_sources = [
            {"f": "Lãi ưu đãi (đầu kỳ)",
             "v": (f"{bank['lai_uu_dai']}%/năm · {bank['uu_dai_thang']} tháng"
                   if co_uu_dai else "— (bỏ giá HouseNow do cao hơn thả nổi)"),
             "s": promo_src if co_uu_dai else "đã loại nguồn không hợp lý"},
            {"f": "Lãi thả nổi (sau ưu đãi)",
             "v": f"{bank['lai_tha_noi']}%/năm", "s": flt_src},
            {"f": "Thời hạn vay tối đa",
             "v": f"{bank['ky_han_max']} năm", "s": promo_src},
            {"f": "Tỷ lệ vay tối đa (LTV)",
             "v": f"{round(bank['ltv_max']*100)}%", "s": promo_src},
            {"f": "Biên độ thả nổi",
             "v": f"+{bank.get('bien_do','?')}%",
             "s": "tham khảo (ảnh HouseNow / ước lượng) — chưa có nguồn realtime"},
            {"f": "Trần trả nợ/thu nhập (DTI)",
             "v": f"{round(bank['dti_max']*100)}%",
             "s": "quy ước nội bộ (~60–70%, ngân hàng ít công bố)"},
        ]

    can_re, re_msg = bank_rates.can_refetch()
    return render_template(
        "vay_von.html",
        field_sources=field_sources,
        result=result,
        appraise=appraise,
        compare=compare,
        story=story,
        banks=bank_rates.bank_choices(),
        banks_json=json.dumps({k: v for k, v in banks.items()}),
        bank=bank,
        bank_key=bank_key,
        rates_meta={"fetched_at": rates.get("fetched_at"),
                    "source": rates.get("source"), "is_demo": rates.get("is_demo")},
        can_refetch=can_re, refetch_msg=re_msg,
        sel={"gia": gia, "thu_nhap": thu_nhap,
             "ty_le_vay": round(ty_le_vay * 100), "lai_suat": sel_lai, "nam": nam},
    )


@app.route("/vay-von/refetch", methods=["POST"])
def vay_von_refetch():
    """Lấy lãi suất MỚI NHẤT theo yêu cầu (chạy fetch_rates). Chặn nếu đã lấy được hôm nay.
    Trả JSON để JS cập nhật, không reload toàn trang."""
    from flask import jsonify
    import bank_rates
    from fetch_rates import run_fetch

    ok, msg = bank_rates.can_refetch()
    if not ok:
        return jsonify({"ok": False, "skipped": True, "msg": msg}), 200
    res = run_fetch()
    if res["ok"]:
        res["msg"] = f"Đã cập nhật: {', '.join(res['updated'])}."
        if res["failed"]:
            res["msg"] += f" Chưa lấy được: {', '.join(res['failed'])}."
    else:
        res["msg"] = ("Chưa lấy được lãi thật (nguồn chặn hoặc chưa cấu hình parse). "
                      "Vẫn dùng mức tham khảo. Thử lại trên mạng 4G/thường.")
    return jsonify(res), 200


# Các trang khảo sát thị trường đã GỘP vào Tổng quan (/). Giữ route cũ → redirect
# để link/bookmark cũ không vỡ; chuyển thẳng tới anchor section tương ứng.
@app.route("/heatmap")
def heatmap():
    return redirect(url_for("dashboard", loai_bds=_loai_bds()) + "#ban-do")


@app.route("/xu-huong")
def xu_huong():
    return redirect(url_for("dashboard", loai_bds=_loai_bds()) + "#xu-huong")


@app.route("/so-nguon")
def so_nguon():
    return redirect(url_for("dashboard", loai_bds=_loai_bds()) + "#so-nguon")


if __name__ == "__main__":
    if db.count() == 0:
        print("DB trống — chạy 'python src/seed.py' để nạp dữ liệu mẫu.")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
