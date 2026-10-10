# ĐẶC TẢ TÍNH NĂNG: HIỂN THỊ HÌNH ẢNH MINH HỌA TRỰC QUAN CHO THẺ NHỰA PVC VÀ VỎ ĐỰNG THẺ

**Dự án:** Tagluxe B2B Social Commerce  
**Ngày thực hiện:** 10-10-2026  
**Trạng thái:** Đã phê duyệt (Chốt phương án Mockup giao diện tương tác động)  
**Tác giả:** Đội ngũ Kỹ thuật Tagluxe  

---

## 1. MỤC TIÊU VÀ BỐI CẢNH
Trước đây trên công cụ tính giá và cấu hình đơn hàng trực tuyến (`price_calculator`):
- Chỉ có danh mục **Dây đeo thẻ** được tích hợp hệ thống Preview ảnh tương tác động: khi chọn phụ kiện (Khóa an toàn, Khóa phụ, Cục thắt, Tăng đơ, Móc đen), khung Preview tự động chuyển sang ảnh phụ kiện, hiển thị lưới ảnh và cho phép bấm phóng to (Lightbox).
- Trong khi đó, ở hai danh mục **Thẻ Nhựa PVC** và **Vỏ Đựng Thẻ**, khi khách hàng thay đổi các tùy chọn cốt lõi:
  - Kiểu dáng: Dáng đứng (Dọc) vs Dáng nằm (Ngang).
  - Quy cách ép màng: Cán màng mờ vs Cán màng bóng vs Cán màng nhám hạt sần.
  - Gia công đục lỗ: Không đục lỗ vs Đục lỗ con nhộng (Oval) vs Đục lỗ tròn.
  - Chất liệu vỏ: Vỏ silicon dẻo vs Vỏ ABS trơn vs Vỏ ABS in UV.
  Khung Preview bên trái chỉ hiển thị một ảnh cố định đại diện chung, chưa phản ánh được chi tiết trực quan của từng tùy chọn, khiến khách hàng khó hình dung sự khác biệt giữa các chất liệu và gia công cơ khí.

Mục tiêu của bản nâng cấp này là đưa trải nghiệm hiển thị hình ảnh trực quan của **Thẻ Nhựa PVC** và **Vỏ Đựng Thẻ** đạt tiêu chuẩn cao cấp "y chang như dây đeo thẻ", giúp khách hàng B2B quan sát rõ ràng từng chi tiết sản phẩm trước khi chốt đơn.

---

## 2. QUY CHUẨN TRẢI NGHIỆM NGƯỜI DÙNG (UI/UX SPECIFICATION)

### 2.1. Danh mục Thẻ Nhựa PVC (`#panel_pvc`)
1. **Cấu trúc 2 Tab cố định:**
   - Phía trên khung Preview bên trái cố định 2 Tabs điều hướng:
     - `[ Mẫu Thẻ Nhựa ]`: Luôn hiển thị ảnh thẻ nhựa PVC nguyên bản (`demo_the_nhua_pvc.jpg`), đại diện cho tổng thể thẻ PVC 4 lớp chuẩn ISO 7810 bo góc. Khi chọn kích thước thẻ hoặc loại ép màng cán (mờ, bóng, nhám), ảnh minh họa tiếp tục giữ nguyên là thẻ nhựa như cũ.
     - `[ Chi Tiết Lỗ Đục ]`: Hiển thị ảnh chụp cận cảnh quy cách đục lỗ cơ khí:
       - Khi chọn **Đục lỗ con nhộng (Oval)**: Hiển thị `demo_the_pvc_lo_ovan.jpg` (lỗ dập 3×15mm chống xoay).
       - Khi chọn **Đục lỗ tròn 5mm**: Hiển thị `demo_the_pvc_lo_tron.jpg` (lỗ tròn 5mm chuẩn xác).
       - Khi chọn **Không đục lỗ**: Hiển thị ảnh thẻ nguyên bản phẳng (`demo_the_nhua_pvc.jpg`).
2. **Cơ chế chuyển Tab thông minh:**
   - Khi khách click chọn **Đục lỗ Oval** hoặc **Đục lỗ Tròn**: Giao diện tự động nhảy sang tab `[ Chi Tiết Lỗ Đục ]` và nạp ảnh minh họa lỗ dập tương ứng để khách hàng dễ dàng hình dung.
   - Khi khách click chọn **Không đục lỗ** hoặc chọn **Màng cán / Kích thước**: Giao diện tự động chuyển về tab `[ Mẫu Thẻ Nhựa ]` và duy trì ảnh thẻ nhựa PVC nguyên bản như cũ.
   - Khách hàng có thể chủ động bấm qua lại giữa 2 tab `[ Mẫu Thẻ Nhựa ]` và `[ Chi Tiết Lỗ Đục ]` bất kỳ lúc nào để so sánh.
3. **Phóng to chi tiết (Lightbox Modal):**
   - Khách có thể click trực tiếp vào ảnh preview ở cả 2 tab để mở modal Lightbox toàn màn hình, xem rõ từng chi tiết sản phẩm.

### 2.2. Danh mục Vỏ Đựng Thẻ (`#panel_holder`)
1. **Góc nhìn tương tác 2 Tab cố định:**
   - Thanh Tabs điều hướng:
     - `[ Kiểu Dáng Vỏ ]`: Xem hình ảnh vỏ thẻ theo **Vỏ thẻ dọc** (Vertical) hoặc **Vỏ thẻ ngang** (Horizontal).
     - `[ Chất Liệu Vỏ ]`: Xem hình ảnh chất liệu vỏ gồm **Vỏ thẻ 3k** (Silicon dẻo trong suốt chống nước) hoặc **Vỏ thẻ 7k** (Nhựa ABS trơn không in / ABS in UV).
2. **Đồng bộ trạng thái trực quan:**
   - Click chọn **Dáng đứng dọc** $\rightarrow$ Tự động chuyển tab `[ Kiểu Dáng Vỏ ]`, nạp ảnh `demo_vo_the_dung.jpg`.
   - Click chọn **Dáng nằm ngang** $\rightarrow$ Tự động chuyển tab `[ Kiểu Dáng Vỏ ]`, nạp ảnh `demo_vo_the_ngang.jpg`.
   - Click chọn **Vỏ 3k (Silicon)** $\rightarrow$ Tự động chuyển tab `[ Chất Liệu Vỏ ]`, nạp ảnh `demo_vo_the_3k.jpg`.
   - Click chọn **Vỏ 7k (ABS trơn)** hoặc **Vỏ ABS in UV** $\rightarrow$ Tự động chuyển tab `[ Chất Liệu Vỏ ]`, nạp ảnh `demo_vo_the_7k.jpg`.
   - Hỗ trợ phóng to Lightbox sắc nét cho cả 2 góc nhìn.

---

## 3. DANH MỤC HÌNH ẢNH VÀ QUY CÁCH KỸ THUẬT

Hệ thống cấu hình danh mục ảnh demo chuẩn quy cách (đặt tại `frontend/storefront/static/images/demo/` và đồng bộ `static/images/demo/`) để người quản trị có thể dễ dàng thay thế bằng hình ảnh chụp thực tế tại xưởng:

| Mã Định Danh | Tên Hiển Thị | Tên File Hình Ảnh | Đặc Điểm Nhận Diện |
| :--- | :--- | :--- | :--- |
| `the_pvc_main` | Thẻ Nhựa PVC Gốc | `demo_the_nhua_pvc.jpg` | Mẫu thẻ PVC 4 lớp chuẩn ISO 7810 bo góc |
| `pvc_hole_capsule` | Lỗ Con Nhộng (Oval) | `demo_the_pvc_lo_ovan.jpg` | Lỗ đột dẹt 3×15mm ở giữa đỉnh thẻ chống xoay lật |
| `pvc_hole_round` | Lỗ Tròn 5mm | `demo_the_pvc_lo_tron.jpg` | Lỗ tròn đường kính 5mm chuẩn xác |
| `holder_vertical` | Vỏ Thẻ Dọc | `demo_vo_the_dung.jpg` | Khung vỏ nhựa chuẩn chiều đứng dọc |
| `holder_horizontal`| Vỏ Thẻ Ngang | `demo_vo_the_ngang.jpg` | Khung vỏ nhựa chuẩn chiều nằm ngang |
| `holder_silicone` | Vỏ Thẻ 3k (Silicon) | `demo_vo_the_3k.jpg` | Silicon dẻo trong suốt kháng nước |
| `holder_plain` | Vỏ Thẻ 7k (Nhựa ABS) | `demo_vo_the_7k.jpg` | Nhựa ABS cứng cáp chống va đập |

---

## 4. BẢO TRÌ VÀ THAY ĐỔI DỮ LIỆU
Toàn bộ danh mục hình ảnh được cấu hình dạng cấu trúc JSON mở rộng (`PREVIEW_CATALOG`) trong frontend và kết nối đồng bộ với API Backend (`/api/accessories`). Khi xưởng chụp ảnh thành phẩm thực tế mới, quản trị viên chỉ cần tải ảnh lên trang Admin hoặc ghi đè file trong thư mục `static/images/demo/` là hệ thống sẽ tự động cập nhật ngay lập tức.
