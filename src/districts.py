"""
Cấu hình các quận/huyện TP.HCM dùng chung cho cả 2 crawler (batdongsan + chotot).

district_id (slug) là khóa chuẩn lưu trong DB (cột district_id).
Ưu tiên crawl các quận GIÁ MỀM trước (Q7, Nhà Bè, Q12, Bình Chánh, Gò Vấp, Thủ Đức);
các quận đắt (Q1, Q3, Q5, Q10...) tạm chưa cần vì ngoài tầm mua của đa số.
"""

from __future__ import annotations

# district_id -> thông tin quận
DISTRICTS: dict[str, dict] = {
    "binh_thanh": {"ten": "Bình Thạnh", "chotot": 13109, "bds": "binh-thanh"},
    "quan_7":     {"ten": "Quận 7",     "chotot": 13102, "bds": "quan-7"},
    "nha_be":     {"ten": "Nhà Bè",     "chotot": 13118, "bds": "nha-be"},
    "quan_12":    {"ten": "Quận 12",    "chotot": 13107, "bds": "quan-12"},
    "binh_chanh": {"ten": "Bình Chánh", "chotot": 13115, "bds": "binh-chanh"},
    "go_vap":     {"ten": "Gò Vấp",     "chotot": 13110, "bds": "go-vap"},
    "thu_duc":    {"ten": "Thủ Đức",    "chotot": 13119, "bds": "thu-duc"},
    # Quận giá mềm khác (bật khi cần): Q8, Bình Tân, Tân Phú, Hóc Môn, Củ Chi
    "quan_8":     {"ten": "Quận 8",     "chotot": 13103, "bds": "quan-8"},
    "binh_tan":   {"ten": "Bình Tân",   "chotot": 13108, "bds": "binh-tan"},
    "tan_phu":    {"ten": "Tân Phú",    "chotot": 13113, "bds": "tan-phu"},
    "hoc_mon":    {"ten": "Hóc Môn",    "chotot": 13117, "bds": "hoc-mon"},
    "cu_chi":     {"ten": "Củ Chi",     "chotot": 13116, "bds": "cu-chi"},
}

# Bộ quận ưu tiên crawl (giá mềm) — mặc định khi không chỉ định
PRIORITY = ["quan_7", "nha_be", "quan_12", "binh_chanh", "go_vap", "thu_duc"]

LABEL = {k: v["ten"] for k, v in DISTRICTS.items()}


def ten(district_id: str) -> str:
    d = DISTRICTS.get(district_id)
    return d["ten"] if d else district_id


import re as _re


def from_addr(addr: str):
    """Suy district_id từ chuỗi địa chỉ quận (vd 'Huyện Nhà Bè, TPHCM' -> 'nha_be').
    Trả None nếu không thuộc bộ quận đã cấu hình."""
    if not addr:
        return None
    for did, info in DISTRICTS.items():
        t = info["ten"]
        if t.startswith("Quận ") and t[5:].isdigit():     # 'Quận 7','Quận 12'...
            if _re.search(r"Quận\s*" + t[5:] + r"\b", addr):
                return did
        elif t in addr:                                    # tên chữ: 'Nhà Bè','Gò Vấp'...
            return did
    return None
