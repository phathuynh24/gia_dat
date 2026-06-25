# Dashboard giá nhà Bình Thạnh

Công cụ nội bộ nắm bắt giá BĐS quận Bình Thạnh, phục vụ định giá theo
**comp method** (so căn tương đồng). Bản MVP chạy local, tự chứa — không cần
Google account, không cần deploy.

> Luồng: **Crawl thủ công → Parser tiếng Việt → SQLite → Web dashboard + Tool định giá**

## Cài đặt

```bash
pip install -r requirements.txt
# (chỉ cần khi muốn crawl thật)
playwright install chromium
```

## Chạy nhanh (có data mẫu sẵn)

```bash
python src/seed.py     # nạp 34 tin mẫu vào DB
python src/app.py      # mở http://127.0.0.1:5000
```

> Windows: nếu lỗi font/encoding ở console, đặt `set PYTHONUTF8=1` trước khi chạy.

Dashboard có: giá/m² TB theo phường (bar), scatter diện tích–giá (bắt outlier),
bảng tin có filter. Trang **Định giá nhanh** trả dải P25/P50/P75.

## Dùng data thật

```bash
python src/crawler.py --pages 20 --out data/crawl_raw.json   # crawl thủ công
python src/import_data.py data/crawl_raw.json                # parse + nạp DB
# parse khó bằng Claude API (cần ANTHROPIC_API_KEY trong .env):
python src/import_data.py data/crawl_raw.json --claude
```

Nhập tay **giá đóng thật** từ team: thêm dòng `source = "thuc_te"` trong
`src/seed.py` hoặc file CSV import (sẽ được đánh nhãn "Giá thật" trên dashboard).

## Cấu trúc

| File | Vai trò |
|------|---------|
| `src/parser.py` | Parse tiêu đề rao tiếng Việt → trường chuẩn (regex; tùy chọn Claude API) |
| `src/db.py` | SQLite schema, truy vấn dashboard, logic định giá P25/P50/P75 |
| `src/crawler.py` | Crawl batdongsan.com bằng Playwright (chạy thủ công) |
| `src/import_data.py` | Parse data thô → nạp DB |
| `src/seed.py` | Nạp data mẫu để chạy thử |
| `src/app.py` + `templates/` | Web app Flask |

## Bám theo plan MVP

| Bước plan | Bản local này |
|-----------|---------------|
| 1. Schema + storage | `src/db.py` (SQLite thay Google Sheets) |
| 2. Crawl + parse + import | `crawler.py` + `parser.py` + `import_data.py` |
| 3. Dashboard | `app.py` + Chart.js (thay Looker Studio) |
| 4. Tool định giá | trang `/dinh-gia` (comp method, thay công thức Sheets) |

## Giai đoạn sau (khi MVP validate được)

PostgreSQL/Supabase · FastAPI · React + Recharts + Mapbox · geocoding + heatmap ·
crawl scheduler. Schema đã có sẵn cột `quan`, `lat`, `lng` để mở rộng quận khác
và làm heatmap mà không phải đổi cấu trúc.
