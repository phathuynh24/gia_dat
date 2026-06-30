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

## 2. Trạng thái THẬT / MOCK từng ngân hàng (cập nhật 2026-06-30)

Ghi chú: "tiết kiệm thật" = LS tiết kiệm 12T cào từ webgia.com; lãi thả nổi của các bank này
là **ước tính** (tiết kiệm thật + biên độ MOCK) chứ chưa phải lãi vay công bố.

| Bank | Lãi ưu đãi | Lãi thả nổi | LTV | Kỳ hạn | Ghi chú |
|------|-----------|-------------|-----|--------|---------|
| **BIDV** | 🔴 mock | 🟡 ước tính (tiết kiệm 5,9% thật + 4,0% mock) | 🔴 mock 85% | 🔴 mock 25n | bank chính của user — ưu tiên lấy thật |
| **Vietcombank** | 🔴 mock | 🟡 ước tính (tiết kiệm 5,9% + 4,0%) | 🔴 mock 70% | 🔴 mock 20n | |
| **VietinBank** | 🔴 mock | 🟡 ước tính (5,9% + 3,8%) | 🔴 mock 80% | 🔴 mock 20n | |
| **Agribank** | 🔴 mock | 🟡 ước tính (5,9% + 3,8%) | 🔴 mock 75% | 🔴 mock 20n | |
| **MB Bank** | 🔴 mock | 🟡 ước tính (4,85% + 4,0%) | 🔴 mock 75% | 🔴 mock 20n | |
| **TPBank** | 🔴 mock | 🟡 ước tính (6,2% + 4,2%) | 🔴 mock 70% | 🔴 mock 20n | |
| **VPBank** | 🔴 mock | 🟡 ước tính (6,6% + 4,5%) | 🔴 mock 75% | 🔴 mock 25n | |
| **Techcombank** | 🔴 mock | 🔴 mock 11,0% | 🔴 mock 70% | 🔴 mock 25n | webgia không có → cần link riêng |
| **ACB** | 🔴 mock | 🔴 mock 11,0% | 🔴 mock 70% | 🔴 mock 20n | webgia không có → cần link riêng |
| **Sacombank** | 🔴 mock | 🔴 mock 11,5% | 🔴 mock 70% | 🔴 mock 25n | webgia không có → cần link riêng |
| **Shinhan Bank** | 🔴 mock | 🔴 mock 9,9% | 🟢 **THẬT 80%** | 🟢 **THẬT 50n** | lãi không công bố trên web (phải liên hệ) |
| **HSBC** | 🔴 mock | 🔴 mock 9,75% | 🔴 mock 70% | 🔴 mock 25n | cần link riêng |

🟢 thật · 🟡 ước tính (1 phần thật) · 🔴 mock

**Tóm tắt:** chưa bank nào THẬT 100%. Phần thật hiện có = LS tiết kiệm 12T của 7 bank
(BIDV, VCB, VietinBank, Agribank, MB, TPBank, VPBank) + LTV/kỳ hạn của Shinhan.

## 3. Link nguồn — bạn điền vào, link nào dùng được sẽ lưu để crawl

Dán link trang có **số liệu** (biểu lãi suất / trang sản phẩm vay có ghi % cụ thể).
Cột "Dùng được?" mình sẽ test & đánh dấu, rồi viết crawler riêng cho từng bank dùng được.

| Bank | Link bạn gửi | Lấy được trường gì | Dùng được? | Ngày test |
|------|--------------|--------------------|-----------|-----------|
| BIDV | _(chờ)_ | | | |
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
