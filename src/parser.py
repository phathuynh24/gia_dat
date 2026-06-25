"""
Parser tin rao BĐS tiếng Việt -> dữ liệu có cấu trúc.

Mặc định dùng regex (không cần API key, chạy ngay). Nếu có ANTHROPIC_API_KEY
trong môi trường, có thể gọi parse_with_claude() cho các tin khó.

Ví dụ:
    "Bán nhà HXH 5m đường DBL P26 BT 4x18 3T giá 6.5 tỷ"
    -> {loai_duong: "hxh", rong_hem: 5.0, phuong: "26", dien_tich: 72.0,
        so_tang: 3, gia: 6.5, ...}
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def _strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt để match abbreviation không dấu (hxh, mt, phuong...)."""
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def _num(s: str) -> float:
    """'4,5' / '4.5' -> 4.5"""
    return float(s.replace(",", "."))


# ---------------------------------------------------------------------------
# Giá -> đơn vị tỷ đồng
# ---------------------------------------------------------------------------

def parse_price(text: str):
    """Trả về giá tính bằng tỷ đồng, hoặc None."""
    t = _strip_accents(text.lower())

    # 1. Thập phân: "4,86 tỷ", "6.5 ty"  (ưu tiên để không bị vỡ bởi dấu phẩy)
    m = re.search(r"(\d+[.,]\d+)\s*t[yi]\b", t)
    if m:
        return round(_num(m.group(1)), 4)

    # 2. Số nguyên tỷ + phần lẻ (trăm triệu): "6 tỷ 500", "6 tỷ 5".
    #    Lookahead loại trường hợp số lẻ thực ra là diện tích ("... tỷ 59,4 m²").
    m = re.search(r"(\d+)\s*t[yi]\s+(\d{1,3})(?!\s*[.,]?\d*\s*m)\b\s*(?:tr(?:ieu)?)?", t)
    if m:
        ty = int(m.group(1))
        le = m.group(2)
        le_val = int(le) / 10 if len(le) == 1 else int(le) / 1000
        return round(ty + le_val, 4)

    # 3. "X tỷ" trơn
    m = re.search(r"(\d+)\s*t[yi]\b", t)
    if m:
        return round(int(m.group(1)), 4)

    # 4. "850 triệu" / "850tr"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*tr(?:ieu)?\b", t)
    if m:
        return round(_num(m.group(1)) / 1000, 4)

    return None


# ---------------------------------------------------------------------------
# Diện tích -> m2
# ---------------------------------------------------------------------------

def parse_area(text: str):
    """Trả về (dien_tich_m2, ngang_m, dai_m). Các phần có thể None."""
    t = _strip_accents(text.lower())

    # Kích thước "4x18", "4.5 x 20", "4,5x18m"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*[x*]\s*(\d+(?:[.,]\d+)?)\s*m?\b", t)
    if m:
        ngang, dai = _num(m.group(1)), _num(m.group(2))
        # kích thước hợp lệ: ngang < 50m, dai < 100m
        if ngang < 50 and dai < 100:
            return round(ngang * dai, 2), ngang, dai

    # "ngang 4.5 dài 20", "ngang 4 sâu 18"
    m = re.search(r"ngang\s*(\d+(?:[.,]\d+)?).*?(?:dai|sau)\s*(\d+(?:[.,]\d+)?)", t)
    if m:
        ngang, dai = _num(m.group(1)), _num(m.group(2))
        if ngang < 50 and dai < 100:
            return round(ngang * dai, 2), ngang, dai

    # "DT 72", "dien tich 72m2", "72 m2", "72m²" (bắt buộc có 'm2'/'m²' hoặc tiền tố DT
    # để tránh nhầm với 'hẻm 4m', 'mặt tiền 5m')
    m = re.search(r"(?:dt|dien tich)\s*(\d+(?:[.,]\d+)?)", t)
    if m:
        return round(_num(m.group(1)), 2), None, None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*m\s*[2²]", t)  # cần ký hiệu mét vuông (m2 / m²)
    if m:
        return round(_num(m.group(1)), 2), None, None

    return None, None, None


# ---------------------------------------------------------------------------
# Số tầng
# ---------------------------------------------------------------------------

def parse_floors(text: str):
    t = _strip_accents(text.lower())

    # "1 tret 2 lau", "tret 3 lau" -> cộng dồn
    tret = 1 if re.search(r"\btret\b", t) else 0
    lau = re.search(r"(\d+)\s*lau", t)
    if lau:
        return tret + int(lau.group(1)) if tret else int(lau.group(1)) + 1

    # "3 tang", "3T", "3 lầu"
    m = re.search(r"(\d+)\s*(?:tang|t\b)", t)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 30:
            return n
    return None


# ---------------------------------------------------------------------------
# Loại đường + rộng hẻm
# ---------------------------------------------------------------------------

def parse_road_type(text: str):
    """
    Trả về 'mat_tien' | 'hxh' (hẻm xe hơi) | 'hem'.
    Ưu tiên tín hiệu hẻm trước: tin 'hẻm sát mặt tiền' là HẺM, không phải mặt tiền.
    """
    t = _strip_accents(text.lower())
    # 1. Hẻm xe hơi / ô tô / xe tải
    if re.search(r"\bhxh\b|\bhxt\b|hem xe hoi|hem o ?to|hem xe tai|hem oto", t):
        return "hxh"
    # 2. Có chữ 'hẻm' -> là hẻm (kể cả 'hẻm sát mặt tiền', 'gần mặt tiền')
    if re.search(r"\bhem\b|trong hem|nha hem|hxh", t):
        return "hem"
    # 3. Mặt tiền thực sự (không có chữ hẻm ở trên)
    if re.search(r"\bmt\b|mat tien|mat pho|nha mat (?:tien|pho)", t):
        return "mat_tien"
    return None


def parse_alley_width(text: str):
    """Rộng hẻm tính bằng mét, vd 'HXH 5m', 'hem 4.5m'."""
    t = _strip_accents(text.lower())
    m = re.search(r"(?:hxh|hem|hxt)\s*(\d+(?:[.,]\d+)?)\s*m\b", t)
    if m:
        return _num(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Phường + hướng
# ---------------------------------------------------------------------------

def parse_ward(text: str):
    """Trả về số/tên phường dạng chuỗi, vd '26', '13', 'Phước Long'."""
    t = _strip_accents(text.lower())
    m = re.search(r"\bp[\.\s]*?(\d{1,2})\b", t)
    if m:
        return m.group(1)
    m = re.search(r"phuong\s+(\d{1,2})\b", t)
    if m:
        return m.group(1)
    return None


_DIRECTIONS = [
    ("dong nam", "Đông Nam"), ("dong bac", "Đông Bắc"),
    ("tay nam", "Tây Nam"), ("tay bac", "Tây Bắc"),
    ("dong", "Đông"), ("tay", "Tây"), ("nam", "Nam"), ("bac", "Bắc"),
]

def parse_direction(text: str):
    t = _strip_accents(text.lower())
    m = re.search(r"huong\s+([a-z\s]+?)(?:[,.]|$|\d)", t)
    scope = m.group(1).strip() if m else t
    for key, val in _DIRECTIONS:
        if key in scope:
            return val
    return None


# ---------------------------------------------------------------------------
# Parse tổng hợp 1 tin
# ---------------------------------------------------------------------------

def parse_listing(title: str, description: str = "", quan: str = "Bình Thạnh") -> dict:
    """Parse tiêu đề + mô tả -> dict các trường chuẩn."""
    text = f"{title or ''} {description or ''}".strip()

    dien_tich, ngang, dai = parse_area(text)
    gia = parse_price(text)
    gia_per_m2 = round(gia / dien_tich * 1000, 2) if (gia and dien_tich) else None  # triệu/m2

    return {
        "tieu_de": (title or "").strip(),
        "quan": quan,
        "phuong": parse_ward(text),
        "loai_duong": parse_road_type(text),
        "rong_hem": parse_alley_width(text),
        "dien_tich": dien_tich,
        "ngang": ngang,
        "dai": dai,
        "so_tang": parse_floors(text),
        "huong": parse_direction(text),
        "gia": gia,                 # tỷ đồng
        "gia_per_m2": gia_per_m2,   # triệu đồng/m2
    }


# ---------------------------------------------------------------------------
# Parse 1 record từ crawler (có sẵn field cấu trúc đáng tin hơn tiêu đề)
# ---------------------------------------------------------------------------

def parse_crawled(record: dict, quan: str = "Bình Thạnh") -> dict:
    """
    record từ crawler: {title, raw_extra ('4,86 tỷ 59,4 m²'), dia_chi ('Phường 5 ...'), url}
    Ưu tiên giá/diện tích từ raw_extra và phường từ dia_chi (chính xác hơn parse tiêu đề).
    """
    title = record.get("title") or ""
    extra = record.get("raw_extra") or ""
    dia_chi = (record.get("dia_chi") or "").replace("\n", " ").strip("· ").strip()

    parsed = parse_listing(title, quan=quan)  # loai_duong, so_tang, huong, hướng...

    if extra:  # giá + diện tích từ block cấu hình của card
        p = parse_price(extra)
        a, ng, da = parse_area(extra)
        if p is not None:
            parsed["gia"] = p
        if a is not None:
            parsed["dien_tich"], parsed["ngang"], parsed["dai"] = a, ng, da

    w = parse_ward(dia_chi)  # phường từ địa chỉ chuẩn
    if w:
        parsed["phuong"] = w

    parsed["dia_chi"] = dia_chi or None
    parsed["url"] = record.get("url")
    g, dt = parsed.get("gia"), parsed.get("dien_tich")
    parsed["gia_per_m2"] = round(g / dt * 1000, 2) if (g and dt) else None
    return parsed


# ---------------------------------------------------------------------------
# (Tùy chọn) Parse bằng Claude API cho tin khó — chỉ chạy khi có API key
# ---------------------------------------------------------------------------

def parse_with_claude(title: str, description: str = "", quan: str = "Bình Thạnh") -> dict:
    """Dùng claude-sonnet-4-6 để parse. Cần ANTHROPIC_API_KEY. Fallback về regex nếu lỗi."""
    import os, json
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return parse_listing(title, description, quan)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        text = f"{title}\n{description}"
        prompt = (
            "Trích xuất thông tin từ tin rao bán nhà tiếng Việt sau thành JSON với các khóa: "
            "phuong (số/tên phường), loai_duong ('mat_tien'|'hxh'|'hem'), rong_hem (m, số), "
            "dien_tich (m2, số), ngang (m), dai (m), so_tang (số), huong (chuỗi), gia (tỷ đồng, số). "
            "Dùng null nếu không có. Chỉ trả về JSON.\n\nTin rao:\n" + text
        )
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        data["tieu_de"] = (title or "").strip()
        data["quan"] = quan
        if data.get("gia") and data.get("dien_tich"):
            data["gia_per_m2"] = round(data["gia"] / data["dien_tich"] * 1000, 2)
        return data
    except Exception:
        return parse_listing(title, description, quan)


if __name__ == "__main__":
    samples = [
        "Bán nhà HXH 5m đường DBL P26 BT 4x18 3T giá 6.5 tỷ",
        "Bán nhà mặt tiền Phan Văn Trị P5 ngang 4.5 dài 20 1 trệt 2 lầu hướng Đông Nam 12 tỷ",
        "Nhà hẻm 4m P13 60m2 3 tầng giá 5 tỷ 500",
        "Bán đất P12 850 triệu 40m2",
    ]
    import json
    for s in samples:
        print(s)
        print(json.dumps(parse_listing(s), ensure_ascii=False, indent=2))
        print("-" * 60)
