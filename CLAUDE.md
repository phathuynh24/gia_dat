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
| `src/crawler_duan.py` | Cào DANH MỤC DỰ ÁN sơ cấp batdongsan (Playwright) → bảng `projects` |
| `src/parser.py` | Parse tin rao tiếng Việt → trường chuẩn (regex; hook Claude API tùy chọn) |
| `src/import_data.py` | Parse data thô crawl → nạp DB (dedupe theo URL) |
| `src/seed.py` | Sinh data MOCK để chạy thử (khác hẳn data thật) |
| `src/db.py` | SQLite + truy vấn dashboard + định giá P25/P50/P75 |
| `src/app.py` + `src/templates/` | Web Flask + Chart.js |
| `src/finance.py` | Vay vốn: lãi 2 GĐ (re-amortize), thẩm định LTV+DTI, so sánh/xếp hạng bank |
| `src/bank_rates.py` | Đọc `data/bank_rates.json` (12 bank, BIDV mặc định), guard `can_refetch()` |
| `src/fetch_rates.py` | Cào LS tiết kiệm THẬT (webgia.com qua Playwright) → suy lãi vay thả nổi |
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
- **Trang `/vay-von`** (`src/finance.py` + `src/bank_rates.py` + `src/fetch_rates.py`):
  - **Lãi suất THẬT theo ngân hàng** (dropdown, mặc định **BIDV**, 12 bank): chọn bank → lãi
    **2 giai đoạn** (ưu đãi đầu kỳ → thả nổi), tính lại khoản trả khi hết ưu đãi (re-amortize).
    Chọn `tu_nhap` để nhập lãi cố định (case khác).
  - **Lãi thả nổi = LS tiết kiệm 12T (THẬT) + biên độ** từng bank. Nút **"Lấy lãi mới nhất"**
    (`POST /vay-von/refetch`) cào LS tiết kiệm thật từ **webgia.com bằng Playwright** rồi cộng
    `bien_do` → lãi thả nổi. **Guard**: `bank_rates.can_refetch()` chặn nếu đã fetch số thật
    trong ngày (`fetched_at==today and not is_demo`). **7/12 bank có trên webgia** (BIDV, VCB,
    VietinBank, Agribank, MB, TPBank, VPBank) → cờ `lai_real=true`; **5 bank webgia KHÔNG công bố**
    (Techcombank, ACB, Sacombank, Shinhan, HSBC) → giữ baseline `lai_tha_noi_goc` (curated), nhãn
    "tham khảo". ⚠️ Match phải **CHÍNH XÁC** theo field `webgia` — từng dùng match lỏng `in` khiến
    'mb' khớp 'techco(mb)ank'/'saco(mb)ank' → lấy nhầm lãi MB (đã sửa). Lãi ưu đãi (campaign) luôn
    curated. Badge + bảng so sánh phân biệt real (●/"lãi thật") vs tham khảo (○/"tham khảo").
  - **Thẩm định vay được/không** (`finance.appraise_loan`): cần ô **thu nhập/tháng** → check
    **LTV** (vay vượt hạn mức bank?) + **DTI** (trả góp ở mức **lãi thả nổi — kịch bản xấu** ≤
    `dti_max`×thu nhập). Trả kết luận Đủ/Chưa đủ + vay tối đa được duyệt + thu nhập tối thiểu.
  - **So sánh & xếp hạng 12 bank** (`finance.compare_banks`): bảng theo đúng tình huống user,
    xếp hạng *duyệt được trước → tổng lãi thấp nhất*. Hạng 1 = "TỐT NHẤT".
  - **UX kể chuyện cho người mua lần đầu**: timeline 2 giai đoạn + callout "cú sốc lãi thả nổi"
    (+% khi hết ưu đãi), khối **TỔNG TIỀN thực bỏ ra** sau N năm (gốc+lãi+vốn tự có) so với giá
    mua (×bội số), rủi ro trong kỳ vay. Params: `gia, thu_nhap, ty_le_vay(%), bank, lai_suat, nam`.
  - ⚠️ Cần `playwright install chromium` để nút refetch chạy. Lãi cố định cũ vẫn tương thích.
  - **Sửa tay (override) — `data/bank_rates_user.json`**: user nhập số thật (sau khi gọi NH/đọc web)
    qua form "✏️ Sửa lãi suất" trên `/vay-von`. Lưu RIÊNG file user, `bank_rates.load()` **merge đè**
    lên data crawl → crawl lại KHÔNG ghi đè số user. Mỗi field sửa có nhãn "✎ bạn nhập" + ngày;
    bảng "Nguồn dữ liệu" ghi "Bạn tự nhập". Nút **"↩︎ Khôi phục về dữ liệu crawl"** = `clear_override`
    (xoá override bank đó → quay lại số crawl). Ô nhập để trống = giữ crawl (placeholder hiện số crawl).
    Routes: `POST /vay-von/edit-bank`, `POST /vay-von/reset-bank`. `bank_rates.EDITABLE` định nghĩa field
    sửa được (LTV/DTI nhập %→lưu 0–1).
- **Trang `/trung-lap`** (SRS Mở rộng 2 — `db.duplicate_clusters()`): gom tin nghi cùng 1 BĐS
  do nhiều môi giới rao. Khóa gom: nhà/đất = (phường, DT làm tròn, số tầng, loại đường);
  chung cư = (phường, dự án, số PN, DT). Hiển thị biên độ giá sàn–trần + giá sàn đàm phán,
  link "Tính vay (giá sàn)". Lưu ý Jinja: tránh đặt key dict tên `items` (đụng `dict.items`).
- **GỘP vào Tổng quan (`/`)**: Bản đồ giá (`heatmap_data`), Xu hướng giá (`trend_data`), So sánh
  nguồn (`source_overall/by_ward`) **không còn trang riêng** — render thành 3 section `<details>`
  gập trong dashboard, **chart lazy-init khi mở** (canvas ẩn → Chart.js đo sai kích thước). Route
  `/heatmap /xu-huong /so-nguon` giữ lại nhưng **redirect 302** về `/#anchor` (link cũ không vỡ;
  vào qua anchor tự mở section + vẽ). Sub-nav nhóm "market" đã bỏ. Có teaser "🔥 Săn hàng ngộp"
  (chỉ số cụm + link, không bê bảng). Mini-card "💰 Tính vay nhanh" đầu trang → nhảy `/vay-von`.
  - Bubble map (cũ /heatmap): KHÔNG dùng tile/geocoding ngoài; Chart.js bubble tại centroid phường
    (`src/geo.py`, xấp xỉ), màu xanh→đỏ theo giá/m², size theo số tin.
- **Trang `/du-an`** (Dự án mở bán — sơ cấp): danh mục dự án chung cư **đang/sắp mở bán** để
  mua trực tiếp từ CĐT (giá tốt hơn thứ cấp). Bảng `projects` (khác `listings`), nạp bằng
  `crawler_duan.py` (Playwright, batdongsan mục dự án, toàn HCM). Lọc theo quận; loại "đã bàn giao".
  ⚠️ batdongsan để **đa số dự án HCM trạng thái "đang cập nhật"** (ít gắn nhãn sắp/đang mở bán) →
  `list_projects` mặc định gồm cả `dang_cap_nhat`. Card nổi bật (sắp/đang mở bán) là TOÀN QUỐC →
  đã loại (chỉ lấy list chính `re__prj-card-full`). Trang chính ~10 dự án, KHÔNG có phân trang `/pN`.
  Giá/CĐT thường ở trang chi tiết (card chỉ có tên/trạng thái/địa chỉ/quy mô) → link ra batdongsan.
  `db.upsert_projects` dedupe theo url. Nav tab riêng "Dự án mở bán".
- **Đồng bộ loại BĐS toàn app**: `loai_bds` **sticky qua session** (giống quận) — chọn ở tab nào
  thì mọi tab giữ nguyên. Mặc định **`chung_cu`** (đứng đầu `LOAI_BDS_LABEL`), rồi nhà riêng, đất nền.
- **Bản đồ vị trí TỪNG tin** (dashboard, cột "Vị trí"): nút `📍 Bản đồ` mỗi dòng → bung hàng
  nhúng **iframe Google Maps** (KHÔNG cần API key). Lazy-load: chỉ nạp lần mở đầu (`toggleMap`).
  ⚠️ **Google embed `q=<địa chỉ text>` KHÔNG thả ghim** với địa chỉ mức đường/phường/quận (chỉ
  canh giữa khu) → user phàn nàn "không thấy marker". CÁCH FIX (đang dùng): khi bấm, JS **geocode
  địa chỉ → toạ độ qua Nominatim/OSM** (`nominatim.openstreetmap.org/search?format=json`, free,
  CORS ok, không key) rồi đưa Google `q=<lat>,<lng>&output=embed` → **LUÔN có ghim**. Nếu Nominatim
  bị chặn/không ra kết quả thì fallback về embed `q=<địa chỉ text>` (canh khu, không ghim).
  Lưu ý: Nominatim rate-limit ~1 req/s — ok vì chỉ gọi khi user bấm từng tin. Mức chính xác =
  đường/phường/quận tuỳ độ chi tiết địa chỉ trích được (KHÔNG phải số nhà — tin rao VN hiếm có).
  Chuỗi địa chỉ dựng bởi filter `app.mapquery`: **bắt buộc có phần CỤ THỂ (tên đường/dự án)**
  thì Google mới thả GHIM — query chỉ mức phường sẽ canh giữa khu, KHÔNG có ghim. Cách trích:
  `_street_from_url` (batdongsan nhúng `-duong-<đường>-phuong-` trong slug),
  `_street_from_title` (chotot/mogi: sau 'đường'/'mặt tiền'/'MT' → các từ Hoa liền nhau, dừng ở
  số/phẩy/chữ thường; ưu tiên keyword 'đường' để né 'Mặt Tiền 4Lầu Đường ...'),
  `_project_from_url` (dự án chung cư sau `-phuong-N-`). Hit-rate ~75% tin Bình Thạnh có tên đường;
  25% còn lại fallback mức phường (không ghim — vì tin rao VN hiếm khi ghi số nhà). Luôn gắn đuôi
  quận + "TP Hồ Chí Minh". Link "Mở trong Google Maps ↗" làm fallback nếu mạng chặn iframe.
  ⚠️ ĐÃ THỬ & BỎ: vẽ marker từng tin bằng Leaflet/centroid phường + jitter → SAI (marker xếp
  thành vòng tròn + rơi xuống sông) vì KHÔNG có toạ độ thật. Bài học: đừng bịa toạ độ —
  để Google geocode từ địa chỉ text là chuẩn nhất khi chưa có lat/lng thật trong DB.
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
