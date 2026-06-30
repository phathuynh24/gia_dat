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


def load() -> dict:
    """Đọc bảng lãi suất. Trả dict {fetched_at, source, is_demo, banks{...}}."""
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("banks"):
            return data
    except (OSError, ValueError):
        pass
    return _FALLBACK


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
