# CLAUDE.md — context cho Claude Code

> File này để Claude Code đọc khi mở project (kể cả trên máy khác). Lịch sử chat KHÔNG
> đồng bộ giữa các máy, nên mọi context quan trọng nằm ở đây.

## Project là gì

Dashboard nội bộ nắm giá BĐS quận Bình Thạnh, phục vụ định giá theo **comp method**
(so căn tương đồng). MVP chạy local, tự chứa — không cần Google account, không deploy.

Luồng: **Crawl thủ công → Parser tiếng Việt → SQLite → Web (Flask + Chart.js)**

## Kiến trúc đã chốt (KHÔNG dùng Google Sheets/Looker như plan gốc)

| File | Vai trò |
|------|---------|
| `src/crawler.py` | Cào batdongsan.com bằng Playwright (chạy thủ công, delay 3–7s + rotate UA) |
| `src/parser.py` | Parse tin rao tiếng Việt → trường chuẩn (regex; hook Claude API tùy chọn) |
| `src/import_data.py` | Parse data thô crawl → nạp DB (dedupe theo URL) |
| `src/seed.py` | Sinh data MOCK để chạy thử (khác hẳn data thật) |
| `src/db.py` | SQLite + truy vấn dashboard + định giá P25/P50/P75 |
| `src/app.py` + `src/templates/` | Web Flask + Chart.js |

## Trạng thái hiện tại

- **945 tin THẬT** đã crawl từ batdongsan (đã commit kèm `data/listings.db`).
- Crawl batdongsan **không bị chặn** (đã chạy 50 trang ổn).
- Data mock (seed.py) và data thật (crawler) phân biệt rõ; dashboard có banner cảnh báo khi đang dùng mock.

## Chạy

```bash
pip install -r requirements.txt
python src/app.py            # http://127.0.0.1:5000 — có data thật sẵn trong DB
# crawl thêm (cần: playwright install chromium):
python src/crawler.py --pages 50 --out data/crawl_raw.json
python src/import_data.py data/crawl_raw.json
```

## Gotchas (đã gặp, đừng lặp lại)

- **Windows console**: đặt `PYTHONUTF8=1` khi chạy script in tiếng Việt, không thì lỗi cp1252.
- **Chart.js vendor local** ở `src/static/`, KHÔNG dùng CDN (môi trường user chặn CDN → trang treo).
- **Parser ưu tiên field cấu trúc**: giá/diện tích lấy từ `raw_extra` ("4,86 tỷ 59,4 m²"),
  phường từ `dia_chi` ("Phường 5") — chính xác hơn parse tiêu đề. Xem `parse_crawled()`.
- **Giá thập phân dùng dấu phẩy** ("4,86 tỷ"): parse_price thử mẫu thập phân TRƯỚC để tránh đọc nhầm thành 86 tỷ.
- **KPI thống kê**: dùng trung vị (median) + P25/P75, KHÔNG dùng mean (bị outlier kéo lệch).
  Đừng làm KPI "mặt tiền đắt hơn hẻm" theo giá/m² — sai bản chất (nhà mặt tiền lô lớn → giá/m² thấp hơn).
- **loai_duong** chỉ ~57% phân loại được từ tiêu đề (mô tả chi tiết không crawl).

## Việc còn để mở (next steps)

- [ ] Dark theme cho khớp mockup thiết kế.
- [ ] Heatmap giá theo khu (cần Google Maps Geocoding key → lat/lng).
- [ ] Parse mô tả chi tiết bằng Claude API để phân loại đường chính xác hơn (cần ANTHROPIC_API_KEY).
- [ ] Nhập tay giá đóng thật từ team (đánh `source = "thuc_te"`).
- [ ] Mở rộng quận khác (schema đã có sẵn cột `quan`).

## Credentials

Chưa có key nào. Khi cần: `cp .env.example .env` rồi điền. File `.env` đã được gitignore.
