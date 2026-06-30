"""
Tính toán vay vốn mua BĐS (trả góp ngân hàng) + thẩm định khả năng vay.

Quy ước đơn vị: giá nhập bằng TỶ đồng, lãi suất %/năm, thời hạn theo NĂM.
Nội bộ tính bằng TRIỆU đồng (1 tỷ = 1000 triệu).

Lãi 2 giai đoạn (đúng cách NHTM VN làm): `uu_dai_thang` tháng đầu hưởng lãi
ưu đãi thấp, sau đó THẢ NỔI ở mức cao hơn. Khi hết ưu đãi, khoản trả hàng tháng
được tính lại (re-amortize) trên dư nợ còn lại theo lãi thả nổi.
"""

from __future__ import annotations


def _annuity(P: float, r_month: float, n: int) -> float:
    """Khoản trả đều hàng tháng cho dư nợ P, lãi tháng r, n kỳ. r=0 → chia đều."""
    if n <= 0:
        return 0.0
    if r_month <= 0:
        return P / n
    f = (1 + r_month) ** n
    return P * r_month * f / (f - 1)


def loan_breakdown(gia_ty: float, ty_le_vay: float = 0.7,
                   lai_suat: float = 10.0, nam: int = 20,
                   lai_uu_dai: float | None = None, uu_dai_thang: int = 0,
                   lai_tha_noi: float | None = None) -> dict:
    """
    gia_ty: giá nhà (tỷ). ty_le_vay: tỷ lệ vay (0–1).
    Lãi: nếu truyền lai_uu_dai + uu_dai_thang + lai_tha_noi → tính 2 GIAI ĐOẠN.
         Nếu không → dùng lai_suat cố định (giữ tương thích cũ).
    Trả breakdown + lịch trả theo năm (re-amortize khi hết ưu đãi).
    """
    gia = float(gia_ty)
    ty_le_vay = min(max(float(ty_le_vay), 0.0), 1.0)
    von_tu_co = round(gia * (1 - ty_le_vay), 3)        # tỷ
    von_vay = round(gia * ty_le_vay, 3)                # tỷ

    n = int(nam) * 12
    if n <= 0:
        return {"loi": "Thời hạn vay phải > 0"}

    # Lãi 2 giai đoạn nếu đủ tham số VÀ ưu đãi THẤP HƠN thả nổi. Nếu ưu đãi ≥ thả nổi
    # (vô lý — thường do nguồn không tin cậy) thì bỏ giai đoạn ưu đãi, tính phẳng thả nổi.
    hai_gd = (lai_uu_dai is not None and lai_tha_noi is not None and uu_dai_thang > 0
              and float(lai_uu_dai) < float(lai_tha_noi))
    if hai_gd:
        r1 = float(lai_uu_dai) / 100 / 12
        r2 = float(lai_tha_noi) / 100 / 12
        promo_m = min(int(uu_dai_thang), n)
    else:
        r1 = r2 = float(lai_suat) / 100 / 12
        promo_m = n

    P = von_vay * 1000                                 # triệu
    inst1 = _annuity(P, r1, n)                          # trả/tháng giai đoạn ưu đãi

    # Chạy month-by-month: trả inst1 trong promo_m, sau đó re-amortize dư nợ ở r2.
    lich = []
    du_no = P
    lai_luy_ke = 0.0
    inst2 = inst1                                       # mặc định (1 giai đoạn)
    inst = inst1
    for m in range(1, n + 1):
        if hai_gd and m == promo_m + 1:                # vừa hết ưu đãi → tính lại
            inst2 = _annuity(du_no, r2, n - promo_m)
            inst = inst2
        r = r1 if m <= promo_m else r2
        lai_thang = du_no * r
        goc_thang = inst - lai_thang
        du_no = max(0.0, du_no - goc_thang)
        lai_luy_ke += lai_thang
        if m % 12 == 0 or m == n:                       # chốt theo năm
            lich.append({
                "nam": (m + 11) // 12,
                "du_no": round(du_no / 1000, 3),
                "lai_luy_ke": round(lai_luy_ke / 1000, 3),
                "goc_da_tra": round((P - du_no) / 1000, 3),
            })

    tong_lai = lai_luy_ke                               # triệu
    tong_tra_nh = P + tong_lai                          # gốc + lãi trả ngân hàng

    return {
        "gia": round(gia, 3),
        "ty_le_vay": round(ty_le_vay * 100),
        "von_tu_co": von_tu_co,
        "von_vay": von_vay,
        "lai_suat": lai_suat,
        "hai_gd": hai_gd,
        "lai_uu_dai": lai_uu_dai,
        "uu_dai_thang": uu_dai_thang if hai_gd else 0,
        "lai_tha_noi": lai_tha_noi,
        "nam": int(nam),
        "tra_thang": round(inst1, 2),                   # ưu đãi (hoặc cố định)
        "tra_thang_uu_dai": round(inst1, 2),
        "tra_thang_tha_noi": round(inst2, 2),           # sau ưu đãi
        "tong_lai": round(tong_lai / 1000, 3),          # tỷ
        "tong_tra": round(tong_tra_nh / 1000 + von_tu_co, 3),  # tỷ (cả vốn tự có)
        "lich": lich,
    }


def appraise_loan(gia_ty: float, thu_nhap_thang: float, bank: dict,
                  ty_le_vay: float, nam: int) -> dict:
    """
    Thẩm định khả năng vay theo LTV + DTI của ngân hàng.

    gia_ty: giá nhà (tỷ). thu_nhap_thang: thu nhập ròng/tháng (triệu).
    bank: cấu hình bank {ltv_max, dti_max, lai_tha_noi, ...}.
    Đánh giá ở mức lãi THẢ NỔI (kịch bản xấu) cho phần trả nợ — an toàn hơn.

    Trả: kết luận Đủ/Thiếu + số tiền vay tối đa được duyệt + thu nhập tối thiểu cần.
    """
    gia = float(gia_ty)
    ltv_max = float(bank.get("ltv_max", 0.7))
    dti_max = float(bank.get("dti_max", 0.6))
    lai_tn = float(bank.get("lai_tha_noi") or bank.get("lai_uu_dai") or 10.5)
    n = int(nam) * 12
    r = lai_tn / 100 / 12

    von_vay = gia * ty_le_vay * 1000                    # triệu

    # (1) LTV: vay quá hạn mức ngân hàng cho phép?
    vuot_ltv = ty_le_vay > ltv_max + 1e-9
    von_vay_max_ltv = gia * ltv_max * 1000              # triệu

    # (2) DTI: khoản trả/tháng (lãi thả nổi) ≤ dti_max × thu nhập?
    tra_thang_tn = _annuity(von_vay, r, n)              # triệu/tháng
    nguong_tra = dti_max * float(thu_nhap_thang) if thu_nhap_thang else 0.0
    dat_dti = thu_nhap_thang and tra_thang_tn <= nguong_tra + 1e-6

    # Số tiền vay tối đa theo thu nhập (đảo annuity từ ngưỡng trả tối đa)
    if thu_nhap_thang and r > 0:
        f = (1 + r) ** n
        von_vay_max_thunhap = nguong_tra * (f - 1) / (r * f)
    elif thu_nhap_thang:
        von_vay_max_thunhap = nguong_tra * n
    else:
        von_vay_max_thunhap = 0.0

    von_vay_max = min(von_vay_max_ltv, von_vay_max_thunhap) if thu_nhap_thang else von_vay_max_ltv
    thu_nhap_toi_thieu = tra_thang_tn / dti_max if dti_max else None

    ly_do = []
    if vuot_ltv:
        ly_do.append(f"Vay {round(ty_le_vay*100)}% vượt hạn mức {round(ltv_max*100)}% "
                     f"({bank.get('ten','NH')}) — cần thêm vốn tự có hoặc tài sản đảm bảo.")
    if thu_nhap_thang and not dat_dti:
        ly_do.append(f"Trả góp {round(tra_thang_tn)} tr/tháng (lãi thả nổi) vượt "
                     f"{round(dti_max*100)}% thu nhập (~{round(nguong_tra)} tr).")

    if not thu_nhap_thang:
        ket_luan = "thieu_tt"                            # chưa nhập thu nhập
    elif not vuot_ltv and dat_dti:
        ket_luan = "du"
    else:
        ket_luan = "thieu"

    return {
        "ket_luan": ket_luan,
        "ltv_max": round(ltv_max * 100),
        "dti_max": round(dti_max * 100),
        "lai_tha_noi": lai_tn,
        "vuot_ltv": vuot_ltv,
        "dat_dti": bool(dat_dti),
        "tra_thang_tha_noi": round(tra_thang_tn, 1),     # triệu/tháng (kịch bản xấu)
        "nguong_tra": round(nguong_tra, 1),
        "thu_nhap_toi_thieu": round(thu_nhap_toi_thieu, 1) if thu_nhap_toi_thieu else None,
        "von_vay_max": round(von_vay_max / 1000, 3),     # tỷ
        "ly_do": ly_do,
    }


def compare_banks(gia_ty: float, thu_nhap_thang: float, ty_le_vay: float,
                  nam: int, banks: dict) -> list[dict]:
    """
    Tính & xếp hạng TẤT CẢ ngân hàng cho đúng tình huống user nhập.

    Mỗi bank: trả góp ưu đãi/thả nổi, tổng lãi, kết luận thẩm định.
    Xếp hạng: ưu tiên DUYỆT ĐƯỢC (nếu có thu nhập) → rồi TỔNG LÃI thấp nhất (rẻ nhất).
    Bank tốt nhất đứng đầu (rank 1).
    """
    rows = []
    for key, b in banks.items():
        nam_eff = min(int(nam), int(b.get("ky_han_max", nam)))   # kẹp theo kỳ hạn tối đa bank
        lb = loan_breakdown(
            gia_ty, ty_le_vay, b["lai_tha_noi"], nam_eff,
            lai_uu_dai=b["lai_uu_dai"], uu_dai_thang=b["uu_dai_thang"],
            lai_tha_noi=b["lai_tha_noi"])
        ap = appraise_loan(gia_ty, thu_nhap_thang, b, ty_le_vay, nam_eff) \
            if thu_nhap_thang else None
        rows.append({
            "key": key, "ten": b["ten"],
            "lai_uu_dai": b["lai_uu_dai"], "uu_dai_thang": b["uu_dai_thang"],
            "lai_tha_noi": b["lai_tha_noi"], "ltv_max": round(b["ltv_max"] * 100),
            "ky_han_max": b["ky_han_max"], "nam_eff": nam_eff,
            "nam_bi_kep": nam_eff < int(nam),
            "tra_uu_dai": lb["tra_thang_uu_dai"], "tra_tha_noi": lb["tra_thang_tha_noi"],
            "tong_lai": lb["tong_lai"],
            "duyet": (ap["ket_luan"] == "du") if ap else None,
            "lai_real": bool(b.get("lai_real")),
            "co_uu_dai": b["lai_uu_dai"] < b["lai_tha_noi"],   # ưu đãi hợp lệ (thấp hơn thả nổi)
        })
    rows.sort(key=lambda r: (0 if r["duyet"] else 1 if r["duyet"] is False else 0,
                             r["tong_lai"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


if __name__ == "__main__":
    import json
    print(json.dumps(loan_breakdown(5.0, 0.7, 10.0, 20,
                                    lai_uu_dai=5.5, uu_dai_thang=24, lai_tha_noi=10.5),
                     ensure_ascii=False, indent=2))
    print(json.dumps(appraise_loan(5.0, 40.0,
                                   {"ten": "BIDV", "ltv_max": 0.85, "dti_max": 0.6,
                                    "lai_tha_noi": 10.5}, 0.7, 20),
                     ensure_ascii=False, indent=2))
