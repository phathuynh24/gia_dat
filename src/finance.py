"""
Tính toán vay vốn mua BĐS (trả góp ngân hàng).

Quy ước đơn vị: giá nhập bằng TỶ đồng, lãi suất %/năm, thời hạn theo NĂM.
Công thức trả góp dư nợ giảm dần KHÔNG dùng ở đây — ta dùng phương thức
"trả góp đều" (annuity) cho con số tham khảo dễ hiểu; kèm lịch theo năm.
"""

from __future__ import annotations


def loan_breakdown(gia_ty: float, ty_le_vay: float = 0.7,
                   lai_suat: float = 10.0, nam: int = 20) -> dict:
    """
    gia_ty: giá nhà (tỷ). ty_le_vay: tỷ lệ vay (0–1, mặc định 70% → vốn tự có 30%).
    lai_suat: %/năm. nam: thời hạn vay.
    Trả về breakdown + lịch trả theo năm (annuity — trả đều hàng tháng).
    """
    gia = float(gia_ty)
    ty_le_vay = min(max(float(ty_le_vay), 0.0), 1.0)
    von_tu_co = round(gia * (1 - ty_le_vay), 3)        # tỷ
    von_vay = round(gia * ty_le_vay, 3)                # tỷ

    n = int(nam) * 12
    r = float(lai_suat) / 100 / 12                      # lãi tháng
    P = von_vay * 1000                                 # triệu đồng (1 tỷ = 1000 triệu)

    if n <= 0:
        return {"loi": "Thời hạn vay phải > 0"}

    if r > 0:
        factor = (1 + r) ** n
        tra_thang = P * r * factor / (factor - 1)       # triệu/tháng
    else:
        tra_thang = P / n

    tong_tra = tra_thang * n
    tong_lai = tong_tra - P

    # Lịch theo năm: dư nợ cuối năm, lãi đã trả luỹ kế, gốc đã trả luỹ kế
    lich = []
    du_no = P
    lai_luy_ke = 0.0
    for y in range(1, int(nam) + 1):
        for _ in range(12):
            lai_thang = du_no * r
            goc_thang = tra_thang - lai_thang
            du_no = max(0.0, du_no - goc_thang)
            lai_luy_ke += lai_thang
        lich.append({
            "nam": y,
            "du_no": round(du_no / 1000, 3),            # tỷ
            "lai_luy_ke": round(lai_luy_ke / 1000, 3),  # tỷ
            "goc_da_tra": round((P - du_no) / 1000, 3), # tỷ
        })

    return {
        "gia": round(gia, 3),
        "ty_le_vay": round(ty_le_vay * 100),
        "von_tu_co": von_tu_co,                         # tỷ — "30% tối thiểu"
        "von_vay": von_vay,                             # tỷ
        "lai_suat": lai_suat,
        "nam": int(nam),
        "tra_thang": round(tra_thang, 2),               # triệu/tháng
        "tong_lai": round(tong_lai / 1000, 3),          # tỷ
        "tong_tra": round((tong_tra) / 1000 + von_tu_co, 3),  # tỷ (cả vốn tự có + trả ngân hàng)
        "lich": lich,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(loan_breakdown(11.2, 0.7, 10.0, 20), ensure_ascii=False, indent=2))
