# TÀI LIỆU PHÂN TÍCH YÊU CẦU PHẦN MỀM (SRS) - HỆ THỐNG BẤT ĐỘNG SẢN SMART DASHBOARD
**Vị trí:** Senior Business Analyst (BA)  
**Dự án:** Hệ thống Thống kê & Định giá Bất động sản Tự động  
**Phiên bản:** v1.0  
**Ngày lập:** 26/06/2026  

---

## 1. Đánh Giá Hiện Trạng Hệ Thống (Qua Hình Ảnh MVP)
Giao diện hiện tại đã đáp ứng tốt bước đầu của một Dashboard phân tích dữ liệu tổng quan (Macro View):
* **Điểm tốt:** Có các chỉ số cốt lõi (Giá trung vị, số lượng tin, khoảng giá phổ biến, diện tích trung vị). Biểu đồ phân bổ giá theo Phường và biểu đồ Phân tán (Scatter Plot) để phát hiện Outlier (biến động giá bất thường) rất trực quan. Có bộ lọc cơ bản theo vị trí và khoảng giá.
* **Hạn chế (Nỗi đau hiện tại):** Hệ thống mới chỉ dừng lại ở mức **"Cho người dùng xem những gì hệ thống có"** chứ chưa **"Trả lời trực tiếp câu hỏi cụ thể của người dùng"** (Micro View). Người dùng phải tự nhìn biểu đồ, tự lọc rồi tự tính toán nhẩm trong đầu.

---

## 2. Phân Tích & Đặc Tả Yêu Cầu Gốc Của User (User Requirement)
* **Yêu cầu gốc:** *"Tôi muốn biết nếu tôi có diện tích cụ thể (ví dụ 80m²), thì ở các Quận/Phường/Địa điểm khác nhau sẽ có giá bao nhiêu tiền dựa trên data thu thập được."*
* **Phân tích của BA:** Đây là bài toán **Ước tính giá tài sản (Property Valuation) dựa trên tham số**. Bản chất người dùng muốn nhập vào 1 biến số cố định (Diện tích) và hệ thống phải trả ra ma trận kết quả (Vị trí vs Giá tiền dự kiến) để so sánh cán cân tài chính.

### Đặc tả tính năng: **"Tìm kiếm & So sánh giá theo diện tích mục tiêu"**
* **Input (Bộ lọc đầu vào):** * Diện tích mục tiêu (Ô nhập số, ví dụ: `80` m²).
    * Khoảng sai số diện tích cho phép (Dropdown: `±5%`, `±10%`, `±15%` để quét dữ liệu lân cận, ví dụ nhập 80m² kèm ±10% sẽ quét các tin từ 72m² - 88m²).
    * Loại hình BĐS (Nhà riêng, Chung cư, Đất nền).
* **Output (Giao diện trả kết quả):** Hệ thống tính toán dựa trên `Giá/m² trung vị` của từng khu vực để kết xuất ra một **Bảng so sánh chi phí** xếp hạng từ thấp đến cao:
    
    | Địa điểm (Phường/Quận) | Giá/m² trung vị | Giá ước tính cho căn 80m² | Số lượng tin mẫu | Đánh giá ngân sách |
    | :--- | :--- | :--- | :--- | :--- |
    | Phường 22, Bình Thạnh | 140 tr/m² | **11.2 Tỷ** | 45 tin | Khớp ngân sách |
    | Phường 19, Bình Thạnh | 190 tr/m² | **15.2 Tỷ** | 30 tin | Vượt ngân sách (+35%) |
    | Phường 26, Bình Thạnh | 145 tr/m² | **11.6 Tỷ** | 82 tin | Khớp ngân sách |

---

## 3. Gợi Ý & Mở Rộng Các Yêu Cầu Tiềm Năng (Khơi phá nhu cầu ẩn của khách hàng)
Là một Senior BA, ngoài việc giải quyết yêu cầu hiện tại, tôi đề xuất tích hợp thêm các "Nỗi đau ngầm" (Latent Pain Points) của nhà đầu tư/người mua nhà để biến Dashboard này thành cỗ máy kiếm tiền:

### Yêu cầu mở rộng 1: Tính năng "Tìm kiếm ngược" (Tìm kiếm theo Ngân sách cố định)
* **Nỗi đau:** Người mua nhà thường có câu hỏi ngược lại: *"Tôi có đúng 5 tỷ trong tay, tôi có thể mua được nhà diện tích bao nhiêu m² và ở khu vực nào tại Bình Thạnh?"*
* **Giải pháp:** Cho phép nhập `Ngân sách tối đa` (ví dụ: 5 Tỷ). Hệ thống sẽ quét toàn bộ dữ liệu và hiển thị danh sách các Phường có mức giá trung bình phù hợp, đi kèm với **Diện tích kỳ vọng tương ứng** (Ví dụ: Với 5 tỷ, ở P27 mua được 45m², nhưng ở P19 chỉ mua được 26m²).

### Yêu cầu mở rộng 2: Tính năng "Lọc sạch tin trùng lặp & Tin môi giới kê giá"
* **Nỗi đau:** Một căn nhà chính chủ gửi 20 môi giới đăng bài với 20 mức giá và tiêu đề khác nhau (gây nhiễu biểu đồ Scatter plot hiện tại của bạn).
* **Giải pháp:** Viết thuật toán Grouping dựa trên: (Diện tích trùng nhau + Số tầng trùng + Vị trí tương đối trong cùng 1 Phường/Đường). Hệ thống sẽ gom tụ lại thành 1 "Cụm tin" và hiển thị: *"Căn nhà này đang được rao bởi 5 môi giới với biên độ giá từ 11.5 Tỷ - 12.2 Tỷ"*. Người xem sẽ biết ngay mức giá sàn để đàm phán.

### Yêu cầu mở rộng 3: Tính năng "Bản đồ nhiệt độ giá" (Heatmap)
* **Nỗi đau:** Nhìn biểu đồ cột (Bar chart) theo Phường rất khó hình dung sự liên kết về mặt địa lý (ví dụ P19 và P21 nằm sát nhau thì giá biến động thế nào).
* **Giải pháp:** Tích hợp Bản đồ số (Map). Khu vực nào giá cao đỏ rực (như trục Nguyễn Hữu Cảnh), khu vực nào giá mềm hơn thì màu xanh lơ. Người dùng click trực tiếp vào một con đường trên bản đồ để xem giá trung bình.

### Yêu cầu mở rộng 4: Tính năng "Lịch sử biến động giá & Dự báo xu hướng"
* **Nỗi đau:** Người mua sợ mua hớ ngay đỉnh sóng, người bán sợ bán hớ lúc đang lên giá.
* **Giải pháp:** Lưu trữ lịch sử cào theo thời gian (Time-series data). Vẽ biểu đồ line hiển thị biên độ tăng trưởng theo tháng/quý. Gắn thêm nhãn AI cảnh báo: `"Khu vực này giá đang tăng nóng 15% trong 2 tháng qua - Rủi ro đu đỉnh cao"`.

---

## 4. Đề Xuất Mô Hình Hóa Luồng Tính Toán (Dành cho Developer)

Để giải quyết yêu cầu cốt lõi "Tính giá cho căn 80m²" của bạn, Dev cần triển khai luồng xử lý dữ liệu sau:

```
[Dữ liệu cào thô từ các Web] 
             │
             ▼
[Bước 1: Data Cleaning] ➔ Lọc bỏ tin rác, tin thiếu giá/diện tích, xử lý Outlier cực đoan.
             │
             ▼
[Bước 2: Phân loại & Grouping] ➔ Nhóm theo Loại hình (Nhà riêng/Chung cư) ➔ Nhóm theo Phường/Tuyến đường.
             │
             ▼
[Bước 3: Tính toán Chỉ số] ➔ Tính Median (Giá/m²) của từng nhóm để làm giá chuẩn (Base Price).
             │
             ▼
[Bước 4: Tham số hóa từ User] ➔ User nhập 80m² ➔ Thuật toán: Estimated_Price = 80 * Median(Giá/m²).
             │
             ▼
[Bước 5: Render UI] ➔ Trả ra bảng so sánh chi phí giữa các khu vực trực quan kèm phân loại ngân sách.
```

## 5. Kết Luận & Khuyến Nghị
Tính năng nhập diện tích để khảo sát giá nhanh theo địa điểm là một tính năng **cực kỳ thực tế và mang tính ứng dụng cao**. Nó chuyển đổi Dashboard của bạn từ một công cụ "đọc báo cáo đơn thuần" thành một **"Công cụ hỗ trợ ra quyết định đầu tư"** (Decision Support Tool). Đây chính là điểm mấu chốt để bạn có thể tiến tới thu phí Premium (SaaS) từ người dùng trong tương lai.