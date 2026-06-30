"""
Lãi suất vay mua nhà các ngân hàng — đọc từ data/bank_rates.json.

Cơ chế (đã chốt với user): app KHÔNG gọi mạng lúc render (môi trường hay chặn).
Thay vào đó đọc file JSON đã được `fetch_rates.py` cập nhật (chạy thủ công trên 4G).
Mỗi bank có: lãi ưu đãi + số tháng ưu đãi, lãi thả nổi, LTV tối đa, kỳ hạn tối đa, DTI tối đa.

Đơn vị: lãi suất %/năm, ltv/dti là tỷ lệ 0–1, kỳ hạn theo năm.
"""

from __future__ import annotations

import datetime
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bank_rates.json")
# Override do USER tự nhập (sau khi gọi NH / đọc web) — lưu RIÊNG để crawl không ghi đè,
# và để có thể KHÔI PHỤC về dữ liệu crawl. Merge đè lên data crawl khi load().
_USER_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bank_rates_user.json")

# Field user được phép sửa tay → (nhãn, kiểu, có phải %/100 không)
EDITABLE = {
    "lai_uu_dai":   ("Lãi ưu đãi (%/năm)", "float", False),
    "uu_dai_thang": ("Số tháng ưu đãi", "int", False),
    "lai_tha_noi":  ("Lãi thả nổi (%/năm)", "float", False),
    "bien_do":      ("Biên độ thả nổi (%)", "float", False),
    "ltv_max":      ("Vay tối đa (% giá trị)", "pct", True),
    "ky_han_max":   ("Kỳ hạn tối đa (năm)", "int", False),
    "dti_max":      ("Trần trả nợ/thu nhập (%)", "pct", True),
}

# Fallback nếu thiếu file (để app không vỡ khi deploy mà chưa có data/bank_rates.json)
_FALLBACK = {
    "fetched_at": None,
    "source": "fallback nội bộ (thiếu data/bank_rates.json)",
    "is_demo": True,
    "banks": {
        "bidv": {"ten": "BIDV", "lai_uu_dai": 5.5, "uu_dai_thang": 24,
                 "lai_tha_noi": 10.5, "ltv_max": 0.85, "ky_han_max": 25,
                 "dti_max": 0.6, "ghi_chu": ""},
    },
}


def load_base() -> dict:
    """Đọc bảng lãi suất CRAWL (chưa merge user override)."""
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("banks"):
            return data
    except (OSError, ValueError):
        pass
    return _FALLBACK


def load_user() -> dict:
    """Đọc override do user nhập tay. {bank_key: {field: value, _edited_at: 'YYYY-MM-DD'}}."""
    try:
        with open(_USER_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_user(d: dict) -> None:
    with open(_USER_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def load() -> dict:
    """Bảng lãi suất ĐÃ MERGE: data crawl + override user (user đè lên). Đánh dấu field
    nào user đã sửa (`_user_fields`) + ngày sửa (`user_edited_at`) để UI hiển thị."""
    data = load_base()
    user = load_user()
    for key, ov in user.items():
        b = data["banks"].get(key)
        if not b:
            continue
        uf = []
        for f, v in ov.items():
            if f.startswith("_"):
                continue
            b[f] = v
            uf.append(f)
        if uf:
            b["_user_fields"] = uf
            b["user_edited_at"] = ov.get("_edited_at")
    return data


def set_override(bank_key: str, fields: dict) -> None:
    """Lưu các field user nhập tay cho 1 bank (merge vào override hiện có)."""
    user = load_user()
    cur = user.get(bank_key, {})
    cur.update({k: v for k, v in fields.items() if v is not None})
    cur["_edited_at"] = datetime.date.today().isoformat()
    user[bank_key] = cur
    save_user(user)


def clear_override(bank_key: str) -> None:
    """Xoá toàn bộ override của 1 bank → quay lại dữ liệu crawl."""
    user = load_user()
    if bank_key in user:
        del user[bank_key]
        save_user(user)


# Khoá ngân hàng mặc định (user dùng BIDV nhiều) — đặt đầu danh sách hiển thị.
DEFAULT_BANK = "bidv"


def can_refetch() -> tuple[bool, str | None]:
    """Cho phép bấm 'Lấy lãi mới nhất'? Chặn nếu đã lấy được số THẬT trong hôm nay."""
    data = load()
    today = datetime.date.today().isoformat()
    if data.get("fetched_at") == today and not data.get("is_demo"):
        return False, f"Đã cập nhật lãi thật hôm nay ({today}) — thử lại vào ngày mai."
    return True, None


def bank_choices() -> list[dict]:
    """Danh sách bank cho dropdown — BIDV trước, kèm config để JS auto điền lãi/LTV."""
    banks = load()["banks"]
    keys = list(banks.keys())
    if DEFAULT_BANK in keys:
        keys.remove(DEFAULT_BANK)
        keys.insert(0, DEFAULT_BANK)
    return [dict(key=k, **banks[k]) for k in keys]
