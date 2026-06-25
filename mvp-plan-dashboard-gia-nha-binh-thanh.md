# MVP Plan — Dashboard giá nhà Bình Thạnh

---

## 1. Idea — mô tả sản phẩm

**Tên sản phẩm:** Dashboard thông tin giá nhà quận Bình Thạnh

**Mục tiêu:** Xây dựng công cụ nội bộ để nắm bắt thông tin giá bất động sản tại quận Bình Thạnh, phục vụ việc định giá các căn tương tự (comp method).

**Người dùng mục tiêu:** Team môi giới / thẩm định giá nội bộ.

**Tính năng cốt lõi:**
- Xem giá/m² trung bình theo phường, loại đường (mặt tiền / hẻm)
- Bảng danh sách tin rao với filter theo tiêu chí
- Tool định giá nhanh: nhập thông số căn → ra dải giá tham chiếu P25–P50–P75
- Heatmap phân bố giá theo khu vực (giai đoạn sau)

**Nguồn dữ liệu:**
- Crawl 1 lần từ batdongsan.com (lọc quận Bình Thạnh)
- Nhập tay bổ sung từ giao dịch thực tế của team (giá trị cao hơn vì là giá đóng thật)

---

## 2. Plan MVP — scope đã thống nhất

> Target: hoàn thành trong ~1 ngày làm việc thực sự (không tính thời gian crawl chạy nền)

### Bước 1 — Thiết kế schema + tạo Google Sheets (~1 giờ)

- Nhờ Claude thiết kế schema chuẩn ngay từ đầu để tránh clean data sau
- Tạo 2 sheet chính:
  - `raw_listings`: data thô từ crawl + nhập tay
  - `pricing_view`: view đã tính giá/m², lọc được theo phường/loại đường
- Các cột cần có: địa chỉ, phường, loại đường (mặt tiền/hẻm), rộng hẻm, diện tích, số tầng, hướng, giá rao, ngày đăng, trạng thái, ghi chú, lat, lng, giá/m² (tính toán)

**Output:** Google Sheets sẵn sàng nhận data

---

### Bước 2 — Crawl 1 lần lấy 300–500 tin (~3–4 giờ)

- Viết Python script dùng **Playwright** (không dùng Scrapy vì batdongsan render JS)
- Chạy thủ công 1 lần trên máy local, output ra CSV
- Sau đó dùng **Claude API** parse tiêu đề listing lộn xộn tiếng Việt → JSON chuẩn
  - VD: `"Bán nhà HXH 5m đường DBL P26 BT 4x18 3T giá 6.5 tỷ"` → `{loai_duong: "hxh", rong_hem: 5, DT: 72, so_tang: 3, gia: 6.5}`
- Import CSV đã parse vào Google Sheets bằng `gspread`

**Lưu ý khi crawl:**
- Thêm delay ngẫu nhiên 3–7s giữa request để tránh bị block
- Rotate user-agent
- Dùng VPN nếu bị chặn IP

**Output:** 300–500 căn trong Sheets, data sạch

---

### Bước 3 — Build dashboard Looker Studio (~2–3 giờ)

- Kết nối Google Sheets → **Google Looker Studio** (free, zero code)
- 3 view cốt lõi:
  1. Giá/m² trung bình theo phường (bar chart)
  2. Scatter plot diện tích vs giá (phát hiện outlier)
  3. Bảng danh sách với filter: phường, loại đường, khoảng giá, khoảng DT
- Tạo calculated field `gia_per_m2 = gia / dien_tich` trực tiếp trong Looker

**Output:** Dashboard chia sẻ được bằng link, không cần login

---

### Bước 4 — Tool định giá trong Sheets (~1 giờ)

- Thêm sheet `dinh_gia`:
  - Input: phường, DT, loại đường
  - Output: P25 / P50 / P75 của giá/m² từ các căn tương đồng
- Dùng công thức `AVERAGEIFS` + `PERCENTILE` + `FILTER`
- Claude viết công thức sẵn, copy-paste vào

**Output:** Tool định giá hoạt động, không cần code

---

### Tổng timeline MVP

| Bước | Việc cần làm | Thời gian ước tính |
|------|-------------|-------------------|
| 1 | Schema + Google Sheets | ~1 giờ |
| 2 | Crawl + parse + import | ~3–4 giờ |
| 3 | Looker Studio dashboard | ~2–3 giờ |
| 4 | Tool định giá Sheets | ~1 giờ |
| **Tổng** | | **~7–9 giờ** |

---

### Quyết định scope MVP

- **Crawl 1 lần thủ công** — không cần cron job, không cần server
- **Google Sheets làm database** — đủ dùng cho <5,000 bản ghi
- **Looker Studio làm frontend** — free, share bằng link, không cần deploy
- **Không có user auth, không cần login** — nội bộ team
- Crawl tự động định kỳ, web app thật → giai đoạn sau khi validate xong MVP

---

## 3. Tech stack

### MVP (hiện tại)

| Layer | Công nghệ | Lý do chọn |
|-------|-----------|-----------|
| Data storage | Google Sheets | Free, không cần setup, share được |
| Crawl | Python + Playwright | JS rendering, dễ debug |
| Parse | Claude API (`claude-sonnet-4-6`) | Parse tiếng Việt lộn xộn tốt hơn regex |
| Import | `gspread` (Python) | Write vào Sheets từ script |
| Dashboard | Google Looker Studio | Kết nối Sheets trực tiếp, zero code |
| Geocoding | Google Maps Geocoding API | Cần cho heatmap |
| Heatmap | kepler.gl (upload CSV) | Free, không cần code |
| Automation | Cowork | Chạy script, quản lý file |

### Giai đoạn tiếp theo (nếu MVP validate được)

| Layer | Công nghệ |
|-------|-----------|
| Database | PostgreSQL via Supabase |
| Backend | FastAPI (Python) |
| Frontend | React + Recharts + Mapbox GL JS |
| Deploy | Vercel (frontend) + Railway/Render (backend) |
| Crawl scheduler | Cron job hàng ngày |
| AI định giá | Claude API nhúng vào web app |

---

## Ghi chú & quyết định còn mở

- [ ] Có dữ liệu giao dịch thực (giá đóng) từ team môi giới không? Nếu có → nhập tay song song với crawl, đánh dấu `source = "thuc_te"`
- [ ] Dashboard Looker dùng nội bộ hay chia sẻ ra ngoài? → ảnh hưởng đến quyết định có cần login không
- [ ] Ngoài Bình Thạnh có mở rộng quận khác không? → schema nên có cột `quan` ngay từ đầu
- [ ] Định nghĩa "tương đồng" cho comp method: cùng phường + cùng loại đường + DT ±20% + giá rao trong 3 tháng gần nhất?
