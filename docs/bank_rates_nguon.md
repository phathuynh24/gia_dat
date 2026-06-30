# Nguồn lãi suất ngân hàng — kế hoạch crawl riêng từng bank

> Mục tiêu: thay dần data MOCK bằng data THẬT cào từ trang chính chủ mỗi ngân hàng.
> Khi bạn tìm được link có số liệu, dán vào cột "Link" bên dưới — link nào dùng được sẽ
> lưu lại để viết crawler riêng (mỗi bank 1 hàm trong `src/fetch_rates.py`).

## 1. Mỗi lần crawl 1 bank cần lấy những gì (schema)

| Trường | Ý nghĩa | Bắt buộc | Hiện lấy từ đâu |
|--------|---------|----------|-----------------|
| `lai_uu_dai` + `uu_dai_thang` | Lãi ƯU ĐÃI cố định + số tháng (vd 6,3%/năm trong 12 tháng). Có bank nhiều gói 12T/24T — lấy gói phổ biến nhất | ✅ | MOCK toàn bộ |
| `lai_tha_noi` | Lãi THẢ NỔI sau ưu đãi (con số quan trọng nhất cho dài hạn) | ✅ | 7 bank = ước tính (tiết kiệm thật + biên độ mock); 5 bank = MOCK |
| `ls_tiet_kiem_12m` | LS tiết kiệm kỳ 12T (để suy thả nổi nếu bank không công bố lãi vay) | tùy | 7 bank THẬT (webgia.com) |
| `bien_do` | Biên độ cộng vào lãi cơ sở/tiết kiệm (≈3,5–4,5%) | ✅ nếu suy từ tiết kiệm | MOCK toàn bộ |
| `ltv_max` | Vay tối đa bao nhiêu % giá trị tài sản (vd 70–85%) | ✅ | Shinhan THẬT (80%); còn lại MOCK |
| `ky_han_max` | Thời hạn vay tối đa (năm) | ✅ | Shinhan THẬT (50n); còn lại MOCK |
| `dti_max` | Trần tỷ lệ trả nợ/thu nhập để thẩm định (≈60–70%) | nên có | MOCK (chính sách nội bộ, ít công bố) |

**Ưu tiên lấy đúng:** `lai_tha_noi` (hoặc `ls_tiet_kiem_12m` + `bien_do`) → `ltv_max` → `ky_han_max`
→ `lai_uu_dai`. Lãi ưu đãi đổi theo campaign nên có thể chấp nhận mock lâu hơn.

## 1b. Nguồn THẬT đang dùng

- **Ảnh HouseNow** (user cung cấp 2026-06) — bảng "So sánh lãi vay BĐS qua HouseNow": cho **7 bank**
  (MB, BIDV, Vietcombank, ACB, VPBank, VietinBank, Agribank) các trường THẬT: lãi ưu đãi (cố định
  12T), **công thức thả nổi** (kỳ tham chiếu + biên độ), thời hạn tối đa, LTV, ân hạn gốc, phí trả
  trước. Lưu vào `data/bank_rates.json` (field `nguon`, `ky_han_tham_chieu`, `bien_do`, `phi_tra_truoc`...).
  ⚠️ Là lãi "qua HouseNow" (môi giới) nên có thể khác lãi vay trực tiếp tại quầy.
- **webgia.com** (Playwright) — LS **tiền gửi** 12T/24T thật → ghép công thức trên ra lãi thả nổi
  cho bank dùng tiền gửi làm cơ sở (BIDV 24T, VCB 12T, VietinBank 24T, Agribank 24T). Bank dùng
  "lãi cơ sở" (MB, ACB, VPBank) → tạm lấy tiền gửi 12T làm xấp xỉ (cờ `tha_noi_uoc_tinh`).
- **shinhan.com.vn** — chỉ LTV 80% + kỳ hạn 50 năm (lãi không công bố).

## 2. Trạng thái THẬT / MOCK từng ngân hàng (cập nhật 2026-06-30)

Ghi chú: "tiết kiệm thật" = LS tiết kiệm 12T cào từ webgia.com; lãi thả nổi của các bank này
là **ước tính** (tiết kiệm thật + biên độ MOCK) chứ chưa phải lãi vay công bố.

| Bank | Lãi ưu đãi | Lãi thả nổi | LTV | Kỳ hạn | Nguồn |
|------|-----------|-------------|-----|--------|-------|
| **BIDV** | 🟢 10%/12T | 🟢 10,2% (tiền gửi 24T 6,0% + 4,2%) | 🟢 80% | 🟢 40n | HouseNow + webgia |
| **Vietcombank** | 🟢 10,5%/12T | 🟢 9,4% (tiền gửi 12T 5,9% + 3,5%) | 🟢 80% | 🟢 30n | HouseNow + webgia |
| **VietinBank** | 🟢 12%/12T | 🟢 10,5% (tiền gửi 24T 6,0% + 4,5%) | 🟢 75% | 🟢 35n | HouseNow + webgia |
| **Agribank** | 🟢 10,5%/12T | 🟢 9,0% (tiền gửi 24T 6,0% + 3,0%) | 🟢 80% | 🟢 35n | HouseNow + webgia |
| **MB Bank** | 🟢 9,9%/12T | 🔴 10,8% mock (cơ sở + 3,5% — chưa cào được lãi cơ sở) | 🟢 80% | 🟢 35n | HouseNow (thiếu cơ sở) |
| **VPBank** | 🟢 9,7%/12T | 🔴 11,8% mock (cơ sở + 3,5% — chưa cào được lãi cơ sở) | 🟢 80% | 🟢 35n | HouseNow (thiếu cơ sở) |
| **ACB** | 🟢 11%/12T | 🔴 11,0% mock (cơ sở + 3,5% — chưa cào được lãi cơ sở) | 🟢 80% | 🟢 30n | HouseNow (thiếu cơ sở) |
| **TPBank** | 🔴 mock | 🟡 10,4% (tiền gửi 12T 6,2% + 4,2% mock) | 🔴 mock 70% | 🔴 mock 20n | webgia (ko có trong ảnh) |
| **Techcombank** | 🔴 mock | 🔴 mock 11,0% | 🔴 mock 70% | 🔴 mock 25n | cần link riêng |
| **Sacombank** | 🔴 mock | 🔴 mock 11,5% | 🔴 mock 70% | 🔴 mock 25n | cần link riêng |
| **Shinhan Bank** | 🔴 mock | 🔴 mock 9,9% | 🟢 80% | 🟢 50n | shinhan.com.vn (LTV/kỳ hạn) |
| **HSBC** | 🔴 mock | 🔴 mock 9,75% | 🔴 mock 70% | 🔴 mock 25n | cần link riêng |

🟢 thật · 🟡 ước tính (1 phần thật) · 🔴 mock

**Tóm tắt:** 7 bank (MB, BIDV, VCB, ACB, VPBank, VietinBank, Agribank) đã có ưu đãi + LTV + kỳ hạn
THẬT từ ảnh HouseNow. Lãi thả nổi: 4 bank thật (BIDV/VCB/VietinBank/Agribank), 2 ước tính (MB/VPBank
dùng lãi cơ sở), ACB chờ base. Còn mock hoàn toàn: Techcombank, Sacombank, HSBC (+ ưu đãi của Shinhan/TPBank).
**Cần thêm link cho:** Techcombank, Sacombank, HSBC (mọi trường); cơ sở ACB; và lãi vay trực tiếp
tại quầy (để đối chiếu với lãi "qua HouseNow").

## 3. Link nguồn — bạn điền vào, link nào dùng được sẽ lưu để crawl

Dán link trang có **số liệu** (biểu lãi suất / trang sản phẩm vay có ghi % cụ thể).
Cột "Dùng được?" mình sẽ test & đánh dấu, rồi viết crawler riêng cho từng bank dùng được.

| Bank | Link bạn gửi | Lấy được trường gì | Dùng được? | Ngày test |
|------|--------------|--------------------|-----------|-----------|
| BIDV | Trang gốc SP vay nhà ở: https://bidv.com.vn/vn/ca-nhan/san-pham-dich-vu/vay-ca-nhan/vay-nhu-cau-nha-o · Trang khuyến mãi vay (lọc gói còn hạn): https://bidv.com.vn/vn/ca-nhan/khuyen-mai/khuyen-mai-vay/ | gói ưu đãi còn hạn (lãi ưu đãi %) | ⏳ chờ test parse | |
| Vietcombank | | | | |
| VietinBank | | | | |
| Agribank | | | | |
| MB Bank | | | | |
| TPBank | | | | |
| VPBank | | | | |
| Techcombank | _(chờ)_ | | | |
| ACB | _(chờ)_ | | | |
| Sacombank | _(chờ)_ | | | |
| Shinhan | https://shinhan.com.vn/vi/personal/vay-the-chap-bat-dong-san.html | LTV 80%, kỳ hạn 50n (lãi: KHÔNG có số) | ⚠️ một phần | 2026-06-30 |
| HSBC | _(chờ)_ | | | |

### ⚠️ Lưu ý khác biệt nguồn (BIDV)
- **bidv.com.vn (trang gốc)**: quảng cáo "lãi suất ưu đãi **từ 3,9%/năm**" (gói khuyến mãi) / "chỉ
  **từ 5%/năm**" — là mức **tối thiểu, nhiều điều kiện** (teaser marketing).
- **HouseNow (ảnh)**: BIDV **10%/12T** — mức thực vay qua môi giới.
- Đang dùng **10% (HouseNow)** vì sát chi phí vay thực tế hơn. Nếu muốn hiển thị "từ 3,9%" thì
  hiểu là sàn quảng cáo. Khi viết crawler BIDV: parse được "từ X%/năm" từ trang khuyến mãi (số có,
  nhưng là mức sàn) → cân nhắc dùng làm `lai_uu_dai_san` riêng, không thay 10%.

### Đã test & KHÔNG dùng được (khỏi thử lại)
- `thebank.vn/*`, `cafef.vn`, `24hmoney.vn`: bảng render JS / không có bảng bank+%.
- `webgia.com/lai-suat/`: ✅ DÙNG ĐƯỢC cho **LS tiết kiệm** (qua Playwright) — đang dùng cho 7 bank.
  Nhưng KHÔNG có Techcombank/ACB/Sacombank/Shinhan/HSBC, và KHÔNG phải lãi vay.
- `webgia.com/lai-suat/<bank>/`: 404 (không có trang per-bank).
- `shinhan.com.vn/...vay-the-chap...`: trang marketing, lãi "cạnh tranh" không có số (chỉ có LTV/kỳ hạn).

## 4. Cách thêm crawler khi có link dùng được
1. Thêm link vào `data/bank_rates.json` (sẽ bổ sung field `nguon` cho từng bank).
2. Viết hàm `fetch_<bank>()` trong `src/fetch_rates.py` (render Playwright + parse số).
3. Đăng ký vào dict điều phối; `run_fetch()` gọi từng hàm, cập nhật + set `lai_real=true`.
4. Field nào không cào được vẫn fallback `*_goc` (mock) và giữ nhãn "tham khảo".
