# TÀI LIỆU ĐẶC TẢ KỸ THUẬT & NGHIỆP VỤ
## TÁCH BỘ ẢNH DEMO VỎ THẺ ABS TRƠN & VỎ THẺ ABS IN UV THEO YÊU CẦU, TỐI ƯU TRANG QUẢN TRỊ ADMIN VÀ BẢNG TÍNH GIÁ STOREFRONT

---

- **Dự án**: Nền tảng Báo giá & Quản trị TAGLUXE
- **Ngày thực hiện**: 10-10-2026
- **Trạng thái**: Đã triển khai & Kiểm thử hoàn tất
- **Môi trường áp dụng**: Worktree & Main Repository (`D:\Antigravity\TAGLUXE`)

---

### 1. BỐI CẢNH VÀ MỤC TIÊU TRIỂN KHAI

#### 1.1. Bối cảnh
Trước đây, hệ thống hiển thị ảnh demo vỏ đựng thẻ chỉ phân biệt theo kiểu dáng dọc/ngang chung chung (`holder_vertical` và `holder_horizontal`), chưa tách biệt giữa **Vỏ Nhựa ABS Trơn (không in)** và **Vỏ Nhựa ABS In UV theo nhận diện thương hiệu**, gây thiếu nhất quán trực quan khi khách hàng cấu hình bảng giá. Đồng thời, trang quản trị cấu hình ảnh demo hiển thị dồn cục, nhiều trường nhập văn bản gây rối mắt.

#### 1.2. Mục tiêu đạt được
1. **Trải nghiệm Storefront tập trung (1 ảnh duy nhất)**:
   - Phần Thẻ nhựa PVC và Vỏ đựng thẻ chỉ hiển thị đúng **1 khung ảnh demo trực quan**, tự động chuyển đổi theo thông số khách chọn.
   - Dây đeo thẻ vẫn duy trì đầy đủ tính năng xem ảnh dây phối và các phụ kiện đính kèm đã chọn.
2. **Quy trình chọn Vỏ đựng thẻ logic**:
   - Khách hàng chọn **Chất liệu & Quy cách** trước (Silicon dẻo / ABS trơn / ABS in UV).
   - Chọn **Kiểu dáng** sau (Dáng đứng dọc / Dáng nằm ngang).
   - **Tùy chọn kích thước thông minh**: Chỉ kích hoạt và hiển thị khối chọn kích cỡ (5.4×8.6cm = 3.000 đ, 7×11cm = 5.000 đ, 9×12cm = 7.000 đ) khi khách chọn **Vỏ Silicon Dẻo**. Khi chọn **Vỏ ABS**, khối kích cỡ tự động ẩn vì vỏ cứng chỉ sản xuất chuẩn cho thẻ ATM (5.4×8.6cm).
3. **Tách biệt 6 ảnh demo Vỏ đựng thẻ chuyên biệt**:
   - Vỏ Silicon dẻo: Dáng đứng dọc & Dáng nằm ngang.
   - Vỏ ABS màu trơn: Dáng đứng dọc & Dáng nằm ngang.
   - Vỏ ABS in UV theo yêu cầu: Dáng đứng dọc & Dáng nằm ngang.
4. **Tối ưu hóa toàn diện Trang Quản trị Admin (`/admin/demo-images`)**:
   - Phân chia 2 Tab rõ ràng: Tab Thẻ nhựa PVC (3 mẫu đục lỗ) và Tab Vỏ đựng thẻ (6 mẫu phân nhóm A, B, C).
   - Hỗ trợ tính năng **1-Click Upload AJAX**: Quản trị viên chỉ cần chọn tệp ảnh thật từ máy tính, ảnh sẽ được upload, lưu cấu hình và cập nhật xem trước ngay lập tức kèm Toast thông báo nổi.
   - Thu gọn các trường tùy chỉnh văn bản (Tiêu đề, Badge) vào Accordion để giao diện thoáng, tinh gọn và dễ sử dụng.

---

### 2. DANH MỤC KHÓA CẤU HÌNH DỮ LIỆU (DATA KEYS SPECIFICATION)

| STT | Khóa cấu hình (Key) | Nhóm sản phẩm | Quy cách & Kiểu dáng | Đường dẫn ảnh mặc định |
|:---:|:---|:---|:---|:---|
| 1 | `pvc_no_hole` | Thẻ nhựa PVC | Nguyên bản không đục lỗ | `/static/images/demo/demo_the_pvc_khong_duc_lo.jpg` |
| 2 | `pvc_oval_hole` | Thẻ nhựa PVC | Đục lỗ dẹt Oval (Con nhộng) chống xoay | `/static/images/demo/demo_the_pvc_lo_ovan.jpg` |
| 3 | `pvc_round_hole` | Thẻ nhựa PVC | Đục lỗ tròn cơ khí tiêu chuẩn 5mm | `/static/images/demo/demo_the_pvc_lo_tron.jpg` |
| 4 | `holder_silicone_vertical` | Vỏ đựng thẻ | Vỏ Silicon dẻo khóa zip — Dáng đứng dọc | `/static/images/demo/demo_vo_silicone_doc.jpg` |
| 5 | `holder_silicone_horizontal` | Vỏ đựng thẻ | Vỏ Silicon dẻo khóa zip — Dáng nằm ngang | `/static/images/demo/demo_vo_silicone_ngang.jpg` |
| 6 | `holder_plain_vertical` | Vỏ đựng thẻ | Vỏ nhựa ABS màu trơn — Dáng đứng dọc | `/static/images/demo/demo_vo_abs_tron_doc.jpg` |
| 7 | `holder_plain_horizontal` | Vỏ đựng thẻ | Vỏ nhựa ABS màu trơn — Dáng nằm ngang | `/static/images/demo/demo_vo_abs_tron_ngang.jpg` |
| 8 | `holder_custom_vertical` | Vỏ đựng thẻ | Vỏ nhựa ABS in UV theo yêu cầu — Dáng đứng dọc | `/static/images/demo/demo_vo_abs_in_doc.jpg` |
| 9 | `holder_custom_horizontal` | Vỏ đựng thẻ | Vỏ nhựa ABS in UV theo yêu cầu — Dáng nằm ngang | `/static/images/demo/demo_vo_abs_in_ngang.jpg` |
| 10 | `lanyard_default` | Dây đeo thẻ | Dây lụa Satin in chuyển nhiệt cao cấp | `/static/images/demo/demo_day_deo_the_chuyen_nhiet.jpg` |

*Ghi chú*: Nhằm đảm bảo tính tương thích ngược (Backward Compatibility), các khóa cũ `holder_vertical` và `holder_horizontal` vẫn được ánh xạ tự động về mẫu ABS trơn tương ứng trong `backend/services/data_service.py`.

---

### 3. QUY TẮC NGHIỆP VỤ & TÍNH TOÁN BÁO GIÁ

#### 3.1. Thẻ nhựa PVC (`pvc`)
- **Tùy chọn đục lỗ**: Không đục lỗ / Lỗ oval / Lỗ tròn — Miễn phí gia công 100% (Đã gồm trong đơn giá thẻ).
- **Màn hình demo**: Hiển thị chính xác ảnh phôi thẻ tương ứng với dạng lỗ khách đã click chọn.

#### 3.2. Vỏ đựng thẻ (`holder`)
- **Dòng 1: Vỏ Silicon Dẻo Trong Suốt (Khóa Zip Chống Nước)**
  - Tùy chọn kích thước lồng thẻ:
    + Kích thước 5.4 × 8.6 cm (Chuẩn ATM): **3.000 đ / cái**
    + Kích thước 7.0 × 11.0 cm (Khổ trung): **5.000 đ / cái**
    + Kích thước 9.0 × 12.0 cm (Khổ lớn): **7.000 đ / cái**
  - Tùy chọn kiểu dáng: Dọc hoặc Ngang (Đồng giá theo kích thước).
- **Dòng 2: Vỏ Nhựa ABS Màu Trơn (Không In)**
  - Đơn giá: **Đồng giá 7.000 đ / cái**.
  - Kích thước: Khung cố định đựng vừa thẻ chuẩn ATM 5.4 × 8.6 cm (Ẩn khối chọn size).
  - Tùy chọn kiểu dáng: Dọc hoặc Ngang (Đồng giá).
- **Dòng 3: Vỏ Nhựa ABS In UV (In Logo & Nhận Diện Theo Yêu Cầu)**
  - Đơn giá: Áp dụng bảng giá lũy tiến theo số lượng từ **20.000 đ đến 35.000 đ / cái**.
  - Kích thước: Khung cố định đựng vừa thẻ chuẩn ATM 5.4 × 8.6 cm (Ẩn khối chọn size).
  - Tùy chọn kiểu dáng: Dọc hoặc Ngang (Đồng giá).

---

### 4. CÁC TỆP NGUỒN ĐÃ THỰC HIỆN CẬP NHẬT

1. **`backend/services/data_service.py`**:
   - Bổ sung cấu hình mặc định `DEFAULT_DEMO_IMAGES` với 6 keys vỏ thẻ chi tiết.
   - Nâng cấp hàm `calculate_holder_price()` nhận diện chính xác chất liệu (`silicone`, `plain`, `custom`), kiểu dáng và kích cỡ để tính đơn giá chuẩn xác.
2. **`backend/admin/routes.py`**:
   - Mở rộng whitelist keys trong `admin_update_demo_images()` và `admin_upload_single_demo_image()` cho phép xử lý lưu trữ và upload độc lập cho cả 6 mẫu vỏ thẻ.
3. **`frontend/admin/templates/demo_images.html`**:
   - Thiết kế lại layout phân Tab (Tab Thẻ PVC & Tab Vỏ đựng thẻ).
   - Tích hợp tính năng tự động upload qua AJAX (`autoUploadFile`) ngay khi chọn tệp ảnh mới.
   - Bổ sung thanh thông báo Toast trạng thái lưu thành công.
4. **`frontend/storefront/templates/components/price_calculator.html`**:
   - Cập nhật từ điển `PREVIEW_CATALOG.holder` hỗ trợ cấu trúc phân tầng: `silicone`, `plain`, `custom`.
   - Hàm `updateProductPreview()` tự động điều phối hiển thị đúng 1 ảnh tương ứng.
   - Điều khiển ẩn/hiện động khối kích thước `#holderSizeBlock` theo lựa chọn chất liệu.
5. **Thư mục ảnh tĩnh (`frontend/storefront/static/images/demo/` & `static/images/demo/`)**:
   - Lưu trữ đầy đủ bộ ảnh demo chất lượng cao cho cả 6 loại vỏ và 3 loại đục lỗ thẻ.

---

### 5. HƯỚNG DẪN DÀNH CHO QUẢN TRỊ VIÊN THAY ẢNH THỰC TẾ

1. Truy cập trang quản trị tại: `http://localhost:5000/admin/demo-images` (Đăng nhập tài khoản Admin).
2. Chuyển sang **Tab Vỏ Đựng Thẻ**.
3. Tại vị trí cần thay ảnh (ví dụ: *Vỏ ABS Trơn — Dáng Đứng Dọc* hoặc *Vỏ ABS In UV — Dáng Nằm Ngang*):
   - Nhấp vào nút **"Đổi Ảnh Mới"**.
   - Chọn tệp ảnh thật chụp sản phẩm từ máy tính cá nhân (định dạng JPG, PNG, WEBP).
   - Hệ thống sẽ tự động upload lên máy chủ, cập nhật ảnh xem trước ngay lập tức và hiển thị thông báo màu xanh "Đã cập nhật ảnh thành công!".
4. Trở về trang chủ Storefront (`http://localhost:5000/`) để kiểm tra hiển thị thực tế trên bảng tính giá của khách hàng.
