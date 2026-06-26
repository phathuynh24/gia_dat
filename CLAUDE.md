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
| `src/crawler_chotot.py` | Cào Chợ Tốt/nhatot qua **API JSON** (không cần Playwright) |
| `src/crawler_mogi.py` | Cào mogi.vn (HTML server-render) — chỉ mức QUẬN, không có phường |
| `src/parser.py` | Parse tin rao tiếng Việt → trường chuẩn (regex; hook Claude API tùy chọn) |
| `src/import_data.py` | Parse data thô crawl → nạp DB (dedupe theo URL) |
| `src/seed.py` | Sinh data MOCK để chạy thử (khác hẳn data thật) |
| `src/db.py` | SQLite + truy vấn dashboard + định giá P25/P50/P75 |
| `src/app.py` + `src/templates/` | Web Flask + Chart.js |
| `src/finance.py` | Tính vay vốn: vốn tự có, trả góp annuity, lịch lãi theo năm |
| `src/districts.py` | Cấu hình quận TP.HCM (mã chotot + slug bds) dùng chung 2 crawler |
| `src/geo.py` | Toạ độ tâm phường Bình Thạnh (xấp xỉ) cho heatmap |
| `src/snapshot.py` | Chụp mốc giá theo thời gian → bảng `price_snapshots` (có cờ `--demo`) |
| `docs/yeu_cau_dashboard_bds.md` | SRS v1 từ BA — so sánh giá, vay vốn, heatmap, time-series |
| `docs/yeu_cau_dashboard_bds_v2.md` | SRS v2 — tái cấu trúc IA (4 tab), giải ngố, chuẩn bị scale |

## Trạng thái hiện tại

- **945 tin THẬT** (nhà riêng) đã crawl từ batdongsan (đã commit kèm `data/listings.db`).
- Crawl batdongsan **không bị chặn** (đã chạy 50 trang ổn).
- Data mock (seed.py) và data thật (crawler) phân biệt rõ; dashboard có banner cảnh báo khi đang dùng mock.
- **Đa loại BĐS** (data THẬT): `loai_bds` = `nha_rieng` (945) | `chung_cu` (281) | `dat_nen` (142),
  tất cả crawl từ batdongsan. Dashboard chia **tab theo loại**, mỗi tab có KPI/biểu đồ/bảng +
  cột phù hợp (chung cư: dự án, số PN, tầng; đất nền: ngang×dài, không tầng).
  Median giá/m²: nhà riêng ~đất, chung cư ~104 tr/m² sàn, đất nền ~131 tr/m² đất.
- File crawl thật: `data/crawl_raw.json` (1457 nhà riêng), `data/crawl_chungcu_dat.json`
  (719 raw chung cư+đất → 423 sau dedup). Crawl chung cư/đất bằng crawler MỚI (đã tag `loai_bds`).
- **Trang `/so-sanh`** (theo SRS `docs/yeu_cau_dashboard_bds.md`) — 2 chế độ:
  - *Theo diện tích* (SRS Mục 2): nhập DT + sai số ±5/10/15% + (tuỳ chọn) ngân sách →
    bảng xếp hạng phường theo giá ước tính = median(giá/m² tin cùng DT±sai số) × DT, kèm
    đánh giá Khớp/Vượt ngân sách. → `db.compare_by_area()`.
  - *Theo ngân sách* (SRS Mở rộng 1): nhập ngân sách → mỗi phường mua được bao nhiêu m².
    → `db.search_by_budget()`.
  - Cả 2 lọc `min_n=3` (bỏ phường nhiễu), tag "ít mẫu" khi n<3. Dùng median (robust outlier).
  - Mỗi dòng có link "Tính vay →" sang `/vay-von` (điền sẵn giá ước tính).
- **Trang `/vay-von`** (`src/finance.py`): nhập giá → vốn tự có tối thiểu (mặc định 30%),
  số tiền vay (70%), trả góp đều hàng tháng (annuity), tổng lãi, lịch dư nợ/lãi luỹ kế theo
  năm + biểu đồ line. Params: `gia, ty_le_vay(%), lai_suat(%/năm), nam`. Mặc định 70%/10%/20 năm.
- **Trang `/trung-lap`** (SRS Mở rộng 2 — `db.duplicate_clusters()`): gom tin nghi cùng 1 BĐS
  do nhiều môi giới rao. Khóa gom: nhà/đất = (phường, DT làm tròn, số tầng, loại đường);
  chung cư = (phường, dự án, số PN, DT). Hiển thị biên độ giá sàn–trần + giá sàn đàm phán,
  link "Tính vay (giá sàn)". Lưu ý Jinja: tránh đặt key dict tên `items` (đụng `dict.items`).
- **Trang `/heatmap`** (SRS Mở rộng 3 — `db.heatmap_data()` + `src/geo.py`): KHÔNG dùng map
  tile/geocoding ngoài (môi trường chặn CDN). Vẽ **bubble map bằng Chart.js**: mỗi phường 1 chấm
  tại centroid (xấp xỉ), màu xanh→đỏ theo giá/m², size theo số tin. Toạ độ là gần đúng.
- **Trang `/xu-huong`** (SRS Mở rộng 4 — bảng `price_snapshots`, `db.record_snapshot/trend_data`):
  line chart median/m² theo thời gian (toàn quận + top phường) + % biến động, cảnh báo "tăng nóng"
  khi ≥10%. Cần ≥2 mốc. Hiện chỉ có 1 đợt crawl → đã sinh **mốc demo** (`snapshot.py --demo`,
  source='demo', banner cảnh báo). Muốn lịch sử THẬT: chạy `python src/snapshot.py` định kỳ
  (cron) sau mỗi đợt crawl, rồi `--clear-demo` để xoá demo.

## Phân loại BĐS (loai_bds) — cách hiển thị đã chốt

| Loại | Thuộc tính đặc thù | Đơn vị giá | Cột bảng |
|------|--------------------|-----------|----------|
| `nha_rieng` 🏠 | loại đường (MT/HXH/hẻm), số tầng, ngang×dài | giá/m² đất | Loại, Tầng, DT |
| `chung_cu` 🏢 | `du_an`, `so_pn`, `so_tang`=tầng căn hộ | giá/m² sàn | Dự án, PN, Tầng, DT |
| `dat_nen` 🟫 | loại đường, ngang×dài, KHÔNG có tầng | giá/m² đất | Loại, KT ngang×dài, DT |

- Tab điều khiển qua query `?loai_bds=...`; mặc định `nha_rieng`. Toàn bộ query/KPI/định giá
  đều lọc theo `loai_bds` (xem `db.stats/avg_price_by_ward/scatter_data/wards/dinh_gia`).
- `parser.parse_property_type()` tự suy loại; khi crawl, `crawler.CATEGORIES` tag sẵn `loai_bds`
  theo chuyên mục URL (chính xác hơn, không phải đoán).

## Nguồn web (đã có + dự kiến mở rộng)

- **batdongsan.com.vn** (`crawler.py`) — Playwright, 3 chuyên mục Bình Thạnh trong `CATEGORIES`.
- **Chợ Tốt / nhatot.com** (`crawler_chotot.py`) — **API JSON** `gateway.chotot.com/v1/public/ad-listing`,
  gọi thẳng HTTP (KHÔNG cần Playwright, không bị 403). Bình Thạnh `area_v2=13109`, region HCM `13000`.
  cg: 1020=nhà, 1010=chung cư, 1040=đất. Tự bỏ tin CHO THUÊ ("…/tháng") + giá thỏa thuận.
- **Tag nguồn**: cột `source` = `batdongsan` | `chotot` | `thuc_te`. Dashboard hiển thị nhãn nguồn
  (cột Nguồn + dòng tổng hợp) để **đối chiếu chéo giá** giữa các site. `SOURCE_LABEL` trong db.py.
- **Đa quận**: `src/districts.py` map district_id → {mã chotot, slug bds}. Cả 2 crawler nhận `--district`.
  Mặc định crawl bộ giá mềm `PRIORITY` (Q7, Nhà Bè, Q12, Bình Chánh, Gò Vấp, Thủ Đức) — quận đắt
  (Q1/3/5/10) tạm bỏ vì ngoài tầm mua. Cột DB: `district_id`, `quan`. Header có **dropdown chọn quận**
  (sticky qua session, mặc định Bình Thạnh). Mọi query lọc theo `district_id` (db `_filt`).
  Median giá/m² nhà: Bình Chánh ~52 < Nhà Bè ~73 < Q12 ~81 < Thủ Đức ~111 < Q7/Gò Vấp ~135 < BT ~160.
- **Lọc rác** (`parser.is_valid_listing`, áp dụng trong `import_data.py`): loại URL quảng cáo,
  tin thiếu giá/DT, giá/m² phi lý (<1 hoặc >2000 tr/m²). Đã dọn 59 tin rác cũ trong DB.
- **mogi.vn** (`crawler_mogi.py`) — HTML server-render, paginate `?cp=N`, lọc quận client-side
  qua `prop-addr` (`districts.from_addr`). ⚠️ list view chỉ có địa chỉ mức QUẬN → `phuong=null`,
  nên mogi chỉ so sánh được ở mức quận. source='mogi'.
- **Trang `/so-nguon`** (So sánh nguồn, trong nhóm Khảo sát thị trường): `db.source_overall()`
  (median/m² 3 nguồn toàn quận, gắn nhãn "cao nhất") + `db.source_by_ward()` (Batdongsan vs Chợ Tốt
  theo phường, chênh ≥15% cảnh báo; mogi loại vì không có phường).
- **Dự kiến thêm**: guland.vn (giá đất + quy hoạch), khung giá đất nhà nước TP.HCM.

## Chạy

```bash
pip install -r requirements.txt
python src/app.py            # http://127.0.0.1:5000 — có data thật sẵn trong DB
# crawl thêm (cần: playwright install chromium):
python src/crawler.py --pages 50 --out data/crawl_raw.json
python src/import_data.py data/crawl_raw.json
```

## Gotchas (đã gặp, đừng lặp lại)

- **Python 3.9**: `db.py` + `parser.py` có `from __future__ import annotations` để cú pháp
  `dict | None` / `str | None` chạy được trên 3.9 (không thì `TypeError` lúc import). Đừng gỡ.
- **Mock chung cư/đất nền**: nạp bằng `python src/seed.py --append --loai chung_cu dat_nen`
  (cờ `--append` để KHÔNG xoá 945 nhà thật). `seed.py` không có `--append` sẽ `clear()` cả DB.
- **Windows console**: đặt `PYTHONUTF8=1` khi chạy script in tiếng Việt, không thì lỗi cp1252.
- **Chart.js vendor local** ở `src/static/`, KHÔNG dùng CDN (môi trường user chặn CDN → trang treo).
- **Parser ưu tiên field cấu trúc**: giá/diện tích lấy từ `raw_extra` ("4,86 tỷ 59,4 m²"),
  phường từ `dia_chi` ("Phường 5") — chính xác hơn parse tiêu đề. Xem `parse_crawled()`.
- **Giá thập phân dùng dấu phẩy** ("4,86 tỷ"): parse_price thử mẫu thập phân TRƯỚC để tránh đọc nhầm thành 86 tỷ.
- **KPI thống kê**: dùng trung vị (median) + P25/P75, KHÔNG dùng mean (bị outlier kéo lệch).
  Đừng làm KPI "mặt tiền đắt hơn hẻm" theo giá/m² — sai bản chất (nhà mặt tiền lô lớn → giá/m² thấp hơn).
- **loai_duong** chỉ ~57% phân loại được từ tiêu đề (mô tả chi tiết không crawl).
- **Phường CHỮ vs SỐ**: quận khác Bình Thạnh có phường tên chữ ("Phường Phú Mỹ", "Xã Tân Nhựt",
  "Thị trấn Nhà Bè"). `parser.extract_ward(dia_chi)` trích cả 2 (không chỉ số). Hiển thị qua Jinja
  filter `wardlabel` (số→"P22", chữ→giữ tên). Sort phường: số trước, chữ sau (`_ward_sort_key`).
- **Bar chart theo phường**: ẩn tự động khi quận không đủ data (`has_ward_chart`, mỗi phường <5 tin) —
  scatter chiếm full width + ghi chú. JS bar chart có guard `if(getElementById)` tránh lỗi khi ẩn.

## Việc còn để mở (next steps)

- [x] Phân loại đa BĐS (nhà riêng / chung cư / đất nền) + tab hiển thị riêng.
- [x] Crawl THẬT chung cư + đất nền batdongsan (281 + 142 tin, đã vào DB).
      Lệnh: `python src/crawler.py --loai chung_cu dat_nen --pages 20` → `import_data.py --append`.
      Lưu ý: ~30% trang bị timeout selector (bot-protection chập chờn) — crawl dư trang để bù.
- [x] SRS Mục 2 (so sánh theo diện tích) + Mở rộng 1 (theo ngân sách) → `/so-sanh`.
- [x] SRS Mở rộng 2 (gom tin trùng/môi giới kê giá) → `/trung-lap`.
- [x] Tính năng vay vốn (vốn tự có 30%, trả góp, lãi theo thời gian) → `/vay-von`.
- [x] SRS Mở rộng 3 (heatmap giá theo phường, bubble map) → `/heatmap`.
- [x] SRS Mở rộng 4 (lịch sử & xu hướng giá) → `/xu-huong` + `snapshot.py` (đang dùng mốc demo).
- [ ] Chụp snapshot THẬT định kỳ (cron) để thay mốc demo bằng lịch sử thật.
- [ ] Toạ độ phường trong geo.py là xấp xỉ — thay bằng geocoding thật nếu cần bản đồ chính xác.
- [x] Lọc tin rác (quảng cáo + thiếu giá/DT + giá phi lý) — `is_valid_listing`, dọn 59 tin.
- [x] Thêm nguồn Chợ Tốt/nhatot qua API (`crawler_chotot.py`) + tag nguồn để đối chiếu chéo.
- [x] Thêm mogi.vn (nguồn 3) + UI `/so-nguon` so sánh giá 3 nguồn (toàn quận) & bds vs chotot (theo phường).
- [ ] Thêm guland.vn (giá đất/quy hoạch).
- [x] **IA v2**: navbar 7 tab → 4 tab chính + sub-nav (Khảo sát / Định giá&So sánh / Săn hàng ngộp / Vay vốn).
- [x] **Giải ngố + tooltip** `(?)`: Giá phổ biến nhất, Khoảng giá bình dân–cao cấp, Tin giá ảo, Phương pháp so sánh thị trường, Mức độ chênh lệch giá.
- [x] **DB scale-ready**: thêm `district_id`/`ward_id`/`street_id` (backfill binh_thanh + số phường).
- [ ] **Scale toàn TP (v2 Mục 4)** — BACKLOG: global filter Quận cascading; bản đồ vector SVG ranh giới phường (thay bubble); cascading input Quận→Phường→Đường (cần `street_id` thật); crawl đa quận.
- [ ] Thêm nguồn nhatot/mogi/guland (selector riêng theo mẫu `crawler.CONFIG`).
- [ ] Dark theme cho khớp mockup thiết kế.
- [ ] Heatmap giá theo khu (cần Google Maps Geocoding key → lat/lng).
- [ ] Parse mô tả chi tiết bằng Claude API để phân loại đường chính xác hơn (cần ANTHROPIC_API_KEY).
- [ ] Nhập tay giá đóng thật từ team (đánh `source = "thuc_te"`).
- [ ] Mở rộng quận khác (schema đã có sẵn cột `quan`).

## Credentials

Chưa có key nào. Khi cần: `cp .env.example .env` rồi điền. File `.env` đã được gitignore.
