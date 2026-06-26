"""
Toạ độ tâm (centroid) các phường quận Bình Thạnh — XẤP XỈ, dùng cho heatmap.

Vì môi trường chặn CDN/map tiles và không có geocoding API, ta KHÔNG vẽ bản đồ
nền thật mà dùng centroid phường để vẽ "bubble map" bằng Chart.js (đã vendor local):
mỗi phường 1 chấm đặt đúng vị trí địa lý tương đối, màu theo giá, size theo số tin.

Toạ độ là gần đúng (đủ để so sánh tương đối giữa các phường). Khi có geocoding thật
(Google/Nominatim) thì backfill lat/lng từng tin để chấm chi tiết hơn.
"""

from __future__ import annotations

# (lat, lng) gần đúng tâm phường Bình Thạnh
WARD_CENTROIDS: dict[str, tuple[float, float]] = {
    "1":  (10.8005, 106.7080),
    "2":  (10.8050, 106.7040),
    "3":  (10.8080, 106.7000),
    "5":  (10.8120, 106.6970),
    "6":  (10.8060, 106.6950),
    "7":  (10.8020, 106.6990),
    "11": (10.7990, 106.7060),
    "12": (10.8080, 106.7120),
    "13": (10.8120, 106.7170),
    "14": (10.8180, 106.7080),
    "15": (10.8150, 106.7020),
    "17": (10.8040, 106.7110),
    "19": (10.7940, 106.7130),
    "21": (10.7990, 106.7200),
    "22": (10.7930, 106.7240),
    "24": (10.8000, 106.7020),
    "25": (10.8150, 106.7220),
    "26": (10.8220, 106.7080),
    "27": (10.8260, 106.7130),
    "28": (10.8300, 106.7060),
}


def centroid(phuong: str):
    """Trả (lat, lng) hoặc None nếu phường không có toạ độ."""
    return WARD_CENTROIDS.get(str(phuong))
