# TÀI LIỆU PHÂN TÍCH BA - TÁI CẤU TRÚC & CHIẾN LƯỢC SCALE DASHBOARD BĐS (v2.0)
**Vị trí:** Senior Business Analyst (BA)
**Dự án:** Hệ thống Thống kê & Định giá Bất động sản Tự động
**Trạng thái:** Đánh giá MVP hiện tại & Đề xuất cải tiến
**Ngày cập nhật:** 26/06/2026

---

## 1. Đánh Giá Tổng Quan Bản MVP Hiện Tại

### Điểm mạnh (Technical Excellence):
* Tốc độ phát triển sản phẩm cực tốt, giao diện trực quan và chuyên nghiệp.
* Tích hợp thành công nhiều tính năng nâng cao và thuật toán phức tạp như: Biểu đồ xu hướng (Line chart), Phân tán dữ liệu phát hiện Outlier (Scatter plot), Thuật toán gom cụm tin trùng (De-duplication), và Bản đồ tọa độ tâm phường tự chế.
* Giải quyết triệt để bài toán minh bạch dữ liệu từ vĩ mô đến vi mô.

### Hạn chế (User Cognitive Overload - Feature Bloat):
* Thanh điều hướng (Navbar) đang quá tải với **7 tab chức năng** hàng ngang (Dashboard, So sánh khu vực, Bản đồ giá, Xu hướng, Vay vốn, Tin trùng, Định giá nhanh).
* Trải nghiệm người dùng (UX) bị phân mảnh: Người dùng phổ thông sẽ bị ngợp, khó định vị được luồng trải nghiệm (User Journey) và không biết nên bắt đầu từ đâu.
* Sử dụng nhiều thuật ngữ đậm chất Toán thống kê và Kỹ thuật, tạo khoảng cách lớn với người dùng ngoài ngành (Môi giới, Người mua nhà phổ thông).

---

## 2. Đề Xuất Tái Cấu Trúc Thông Tin (Information Architecture - IA v2)

Để giảm tải cho thanh điều hướng và tối ưu hóa trải nghiệm, 7 tab hiện tại sẽ được gom nhóm logic lại thành **4 Tab chính** dựa trên mục đích sử dụng (User Intent):

```
[Giá Nhà TP.HCM] (Tên mới khi scale)
├── 1. Khảo sát thị trường (Gom: Dashboard + Bản đồ giá + Xu hướng)
├── 2. Công cụ định giá (Gom: Định giá nhanh + So sánh khu vực)
├── 3. Săn hàng ngộp (Đổi tên từ "Tin trùng" để tăng chuyển đổi)
└── 4. Tính dòng tiền (Gom: Vay vốn - có thể tích hợp làm widget phụ)
```

### Chi tiết cách gom và sắp xếp giao diện:

### 1. Tab: Khảo sát thị trường (Market Insights)
* **Bản chất:** Góc nhìn vĩ mô (Macro View).
* **Cách gom:** Bê nguyên trang `Dashboard` làm màn hình chính của tab này. Tích hợp biểu đồ `Xu hướng giá` và `Bản đồ nhiệt` thành các sub-section (hoặc sub-tab) bên trong màn hình Dashboard thay vì để tách rời ngoài Navbar.

### 2. Tab: Định giá & So sánh (Valuation Tools)
* **Bản chất:** Góc nhìn vi mô (Micro View) cho một bất động sản cụ thể.
* **Cách gom:** Hợp nhất màn hình `Định giá nhanh` và `So sánh khu vực`.
* **Trải nghiệm UX:** Cho người dùng một thanh Toggle/Tab Switcher ở đầu trang để chọn: `[Tính giá theo căn cụ thể]` hoặc `[So sánh giá giữa các phường]`.

### 3. Tab: Săn hàng ngộp (Deal Finder)
* **Bản chất:** Tính năng "Killer Feature" giúp giữ chân user.
* **Cách đổi tên:** Thay thuật ngữ "Tin trùng" bằng **"Săn hàng ngộp / Check môi giới kê giá"**.
* **Trải nghiệm UX:** Giữ logic gom cụm tin trùng, làm nổi bật biên độ chênh lệch giá sàn - giá trần.

### 4. Tab: Tính vay vốn (Financial Calculator)
* **Bản chất:** Công cụ bổ trợ sau khi đã tìm được nhà hoặc định giá xong.
* **Cách gom:** Giữ làm tab phụ, HOẶC biến thành **Action Button** gắn trực tiếp ở kết quả trang *Định giá* và bảng *So sánh chi phí*.

---

## 3. Bản Dịch Thuật Ngữ "Giải Ngố" (De-jargonizing)

Toàn bộ nhãn (Labels) cần chuyển từ "Toán học/Kỹ thuật" sang "Ngôn ngữ thị trường", kèm icon `(?)` tooltip khi hover:

| Thuật ngữ kỹ thuật hiện tại | Thuật ngữ đề xuất hiển thị | Nội dung Tooltip |
| :--- | :--- | :--- |
| **Giá/m² đất trung vị** | **Giá phổ biến nhất** | Mức giá nằm chính giữa thị trường (một nửa cao hơn, một nửa thấp hơn). Chính xác hơn "Giá trung bình" vì không bị lệch bởi vài căn quá đắt/quá rẻ. |
| **Khoảng giá phổ biến (P25-P75)** | **Khoảng giá bình dân - cao cấp** | 50% nhà đất đang rao trong tầm giá này. Giúp xác định ngân sách thuộc nhóm số đông hay thiểu số. |
| **Phát hiện outlier** | **Tin đăng giá ảo / Bất thường** | Căn rẻ bất thường (tin giả, thiếu số 0) hoặc quá đắt (ngáo giá). Hệ thống lọc riêng để tránh sai lệch thống kê. |
| **Comp method** | **Phương pháp so sánh thị trường** | Tính giá dựa trên 5-10 BĐS tương đồng nhất đang bán sát khu vực tìm kiếm. |
| **Biên độ giá** | **Mức độ chênh lệch giá** | Khoảng cách giá rao rẻ nhất ↔ đắt nhất cho *cùng một căn* giữa các môi giới. Giúp nắm giá đáy để đàm phán. |

---

## 4. Chiến Lược Kiến Trúc Khi Mở Rộng (Scale Toàn TP.HCM)

1.  **Cơ chế Lọc Toàn Cục (Global Filter Hierarchy):** Đổi tiêu đề cố định `"Giá nhà Bình Thạnh"` thành Cascading Dropdown `[TP.HCM] ➔ [Quận/Huyện]`. Đổi quận → reload toàn bộ state/data các tab.
2.  **Tối Ưu Bản Đồ Nhiệt:** Bong bóng Grid Lat/Lng sẽ quá tải khi scale. Giải pháp: **Bản đồ Vector SVG ranh giới Quận/Phường VN** (nhẹ, không cần map server ngoài), fill màu theo giá.
3.  **Phân Cấp Bộ Lọc Đầu Vào:** `Định giá nhanh` chọn `Quận` ➔ API lấy `Phường` ➔ `Tuyến đường`. Gọn UI + giảm payload.

---

## 5. Kết Luận & Hành Động Tiếp Theo (Action Items)

* [x] **Bước 1:** Gộp giao diện theo IA v2 → navbar còn **4 Tab chính** (+ sub-nav).
* [x] **Bước 2:** Cập nhật nhãn theo bảng "Giải ngố" + thêm Tooltip cho Median/P25-P75/Outlier/Comp/Biên độ.
* [x] **Bước 3:** Bổ sung trường DB `district_id`, `ward_id`, `street_id` chuẩn bị import đa quận.

> Trạng thái triển khai & backlog: xem cuối file này.

---

## 6. Trạng Thái Triển Khai (cập nhật bởi Dev)

### ĐÃ LÀM trong v2
- **IA v2 — 4 tab chính**: Khảo sát thị trường (Tổng quan/Bản đồ/Xu hướng) · Định giá & So sánh
  (Định giá theo căn / So sánh phường) · Săn hàng ngộp · Tính vay vốn. Dùng sub-nav theo nhóm,
  giữ nguyên route cũ. (`base.html`)
- **Giải ngố + Tooltip**: nhãn đổi sang ngôn ngữ thị trường, thêm component `(?)` hover-tooltip
  cho Giá phổ biến nhất, Khoảng giá bình dân–cao cấp, Tin giá ảo/bất thường, Phương pháp so sánh
  thị trường, Mức độ chênh lệch giá. (`base.html` .help + các template)
- **DB chuẩn bị scale**: thêm cột `district_id`, `ward_id`, `street_id`; backfill `district_id`
  = `binh_thanh`, `ward_id` = số phường hiện có. (`db.py` `_migrate`)
- Đổi tên trang Tin trùng → **"Săn hàng ngộp / Check môi giới kê giá"**.

### CÒN TRONG BACKLOG (chưa làm) — kèm nhãn độ khó

Nhãn: 🟢 Dễ · 🟡 Trung bình · 🔴 Khó · ⛔ Blocked (chờ data/việc khác)

| Task | Độ khó | Công sức | Phụ thuộc / ghi chú |
|------|--------|----------|---------------------|
| UI so sánh giá Batdongsan vs Chợ Tốt theo phường | 🟢 Dễ | ~0.5 ngày | Data đã tag `source` sẵn; chỉ cần query group by source+phường + 1 view |
| Snapshot lịch sử THẬT định kỳ (cron) thay demo | 🟢 Dễ | ~0.5 ngày | Hạ tầng `snapshot.py` xong; chỉ cần đặt cron + chờ tích luỹ mốc |
| ~~Crawl thật các quận khác (lấp `district_id`)~~ | ✅ XONG | — | Đã crawl 6 quận giá mềm (Q7, Nhà Bè, Q12, Bình Chánh, Gò Vấp, Thủ Đức) qua Chợ Tốt + batdongsan; thêm dropdown chọn quận sticky + filter `district_id` toàn bộ query |
| Bản đồ Vector SVG ranh giới Quận/Phường (Mục 4.2) | 🟡 TB | ~2 ngày | Cần file GeoJSON/SVG ranh giới hành chính TP.HCM + logic fill choropleth |
| Geocoding lat/lng THẬT cho heatmap | 🟡 TB | ~1–2 ngày | Nominatim/OSM free (rate-limit) hoặc Google key; chất lượng địa chỉ cào ảnh hưởng |
| ~~Thêm nguồn mogi.vn~~ | ✅ XONG | — | `crawler_mogi.py` (HTML); lưu ý chỉ mức quận (không phường) |
| ~~UI so sánh giá 3 nguồn theo phường~~ | ✅ XONG | — | `/so-nguon`: 3 nguồn toàn quận + Batdongsan vs Chợ Tốt theo phường |
| Thêm nguồn guland.vn (giá đất/quy hoạch) | 🔴 Khó | ~2–3 ngày | Cấu trúc map/quy hoạch phức tạp, dữ liệu dạng khác |
| Global Filter `[Quận]` (Mục 4.1) | 🟡 ĐÃ LÀM PHẦN LỚN | — | ✅ Dropdown chọn quận (sticky session) + filter `district_id` mọi query. Còn lại: dropdown cấp TP (đa tỉnh) — chưa cần |
| Cascading input Quận→Phường→Đường (Mục 4.3) | 🔴 Khó | ~2–3 ngày | ⛔ Blocked: cần `street_id` data thật (phải cào tên đường chi tiết — hiện chưa có) |
