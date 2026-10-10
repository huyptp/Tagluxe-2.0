# ĐẶC TẢ KỸ THUẬT: QUẢN LÝ BỘ ẢNH DEMO BÁO GIÁ VÀ ĐỒNG BỘ STOREFRONT

**Dự án:** TagLuxe 2.0 — Xưởng Sản Xuất Dây Đeo Thẻ & Thẻ Nhựa Cao Cấp  
**Ngày thực hiện:** 10/10/2026  
**Trạng thái:** Đã triển khai & Kiểm thử thành công 100%  

---

## 1. MỤC TIÊU & NGUYÊN TẮC NGHIỆP VỤ

### 1.1. Yêu cầu của người dùng
1. **Phần Dây đeo thẻ (`lanyard`)**:
   - Cho phép khách hàng xem mẫu dây theo bản rộng (`1.5cm`, `2.0cm`, `2.5cm`).
   - Tự động hiển thị thanh sub-tabs (`Mẫu Dây Đeo` / `Phụ Kiện`) khi khách chọn phụ kiện.
   - Khi khách xem phụ kiện: Chọn 1 phụ kiện thì hiển thị ảnh đơn lớn sắc nét (kèm tên, giá, mô tả), chọn từ 2 phụ kiện trở lên thì hiển thị lưới 2 cột trực quan.
   - **Trường hợp khách không chọn phụ kiện đi kèm**: Hiển thị ảnh demo trực quan tương ứng theo kích thước bản rộng dây đeo (`1.5cm`, `2.0cm chuẩn`, `2.5cm`).
2. **Phần Thẻ nhựa PVC (`pvc`)**:
   - **Chỉ hiển thị đúng 1 ảnh demo duy nhất** (không tách tab, không lưới đa ảnh).
   - Ảnh demo tự động chuyển đổi trực tiếp theo quy cách đục lỗ:
     - *Không đục lỗ*: Hiển thị ảnh thẻ nguyên bản bo tròn 4 góc (`demo_the_pvc_khong_duc_lo.jpg`).
     - *Đục lỗ oval (con nhộng)*: Hiển thị ảnh thẻ có lỗ dập con nhộng 3x15mm chuẩn cơ khí chống xoay (`demo_the_pvc_lo_ovan.jpg`).
     - *Đục lỗ tròn (5mm)*: Hiển thị ảnh thẻ có lỗ dập tròn 5mm sắc gọn (`demo_the_pvc_lo_tron.jpg`).
3. **Phần Vỏ đựng thẻ (`holder`)**:
   - Hiển thị ảnh demo trực quan theo chất liệu (Silicon, ABS trơn, ABS in UV) và định hướng (Dọc / Ngang).
4. **Trang Quản trị Admin (`/admin/demo-images`)**:
   - Bổ sung Tab **Dây Đeo Thẻ** (3 kích thước bản rộng: 1.5 cm, 2.0 cm chuẩn, 2.5 cm) bên cạnh 2 tab Thẻ PVC và Vỏ Thẻ.
   - Admin có thể xem trước thumbnail, đổi ảnh tải lên từ máy tính cá nhân hoặc nhập đường dẫn trực tiếp, tùy chỉnh tên hiển thị và nhãn badge linh hoạt.

---

## 2. THIẾT KẾ KIẾN TRÚC & DỮ LIỆU

### 2.1. Quản lý cấu hình dữ liệu (`backend/services/data_service.py`)
- Định nghĩa cấu hình mặc định `DEFAULT_DEMO_IMAGES` với đầy đủ đường dẫn ảnh, nhãn badge (`pill`), tiêu đề và mô tả.
- Hàm `get_demo_images_config()`: Tải cấu hình từ `storage/demo_images.json` (nếu có cập nhật) hoặc nạp fallback an toàn.
- Hàm `save_demo_images_config(data)`: Lưu các cập nhật mới vào `storage/demo_images.json`.
- Tích hợp tự động vào `get_accessories_catalog()` để Storefront nhận được toàn bộ dữ liệu chỉ trong 1 lần gọi API.

### 2.2. Tuyến đường Quản trị Admin (`backend/admin/routes.py`)
- `GET /admin/demo-images`: Màn hình giao diện quản lý ảnh demo báo giá.
- `POST /admin/demo-images/update`: Tiếp nhận cập nhật đồng loạt (bao gồm tệp tải lên từ máy tính hoặc đường dẫn ảnh tĩnh).
- `POST /admin/demo-images/upload-single/<key>`: API tải ảnh nhanh cho từng mục thông qua AJAX.
- Xác thực bảo mật: Bắt buộc đăng nhập (`@login_required`), kiểm tra CSRF token, xác thực header bytes hình ảnh (`is_valid_image_file`).
- Ghi nhật ký kiểm toán hệ thống (`record_audit`).

### 2.3. Tuyến đường API Storefront (`backend/api/routes.py`)
- `GET /api/demo-images`: Trả về dữ liệu JSON cấu hình ảnh demo hiện hành.
- `GET /api/accessories`: Trả về danh mục phụ kiện kết hợp trường `demo_images`.

### 2.4. Giao diện Người dùng Báo giá (`frontend/storefront/templates/components/price_calculator.html`)
- Cấu trúc `calcPreviewCard`:
  - Khung ảnh đơn `calcPreviewSingleWrap` hiển thị ảnh demo phóng to, hỗ trợ lightbox chi tiết.
  - Sub-tabs `calcPreviewTabs` và lưới `calcPreviewGridWrap` tự động ẩn khi ở danh mục Thẻ PVC / Vỏ thẻ, và chỉ hiển thị khi ở danh mục Dây đeo có chọn phụ kiện.
- Hàm `updateProductPreview()`:
  - Phân luồng rành mạch giữa Dây đeo (đa góc nhìn, phụ kiện) và Thẻ nhựa / Vỏ thẻ (1 ảnh duy nhất chuyển đổi theo lựa chọn).
  - Tự động đồng bộ ảnh từ server (`syncAccessoriesFromDB`) khi tải trang.

---

## 3. KẾT QUẢ KIỂM THỬ THỰC TẾ

| Hạng mục kiểm tra | Phương thức | Kết quả mong đợi | Trạng thái thực tế |
|---|---|---|---|
| Trang chủ Storefront | `GET /` | HTTP 200 OK, đầy đủ khung Preview & Tabs dây đeo | **PASS (200 OK)** |
| API Demo Images | `GET /api/demo-images` | JSON `success: true`, đầy đủ các key PVC và Holder | **PASS (200 OK)** |
| API Accessories | `GET /api/accessories` | JSON có trường `demo_images` | **PASS (200 OK)** |
| Trang Admin Demo Images | `GET /admin/demo-images` | HTTP 200 OK, chỉ gồm Thẻ PVC và Vỏ thẻ | **PASS (200 OK)** |
| Cập nhật form Admin | `POST /admin/demo-images/update` | HTTP 200 OK, dữ liệu lưu vào `storage/demo_images.json` | **PASS (200 OK)** |
| Ảnh Thẻ PVC không đục lỗ | `HEAD /static/images/demo/demo_the_pvc_khong_duc_lo.jpg` | HTTP 200 OK | **PASS (200 OK)** |
| Ảnh Thẻ PVC lỗ oval | `HEAD /static/images/demo/demo_the_pvc_lo_ovan.jpg` | HTTP 200 OK | **PASS (200 OK)** |
| Ảnh Thẻ PVC lỗ tròn | `HEAD /static/images/demo/demo_the_pvc_lo_tron.jpg` | HTTP 200 OK | **PASS (200 OK)** |
| Ảnh Vỏ thẻ dáng đứng | `HEAD /static/images/demo/demo_vo_the_dang_doc.jpg` | HTTP 200 OK | **PASS (200 OK)** |
| Ảnh Vỏ thẻ dáng ngang | `HEAD /static/images/demo/demo_vo_the_dang_ngang.jpg` | HTTP 200 OK | **PASS (200 OK)** |
