# ĐẶC TẢ TÍNH NĂNG: KÍCH THƯỚC VỎ SILICON DẺO & TỐI ƯU TRANG ADMIN ẢNH DEMO

**Ngày thực hiện:** 10-10-2026  
**Dự án:** TAGLUXE E-Commerce Platform  
**Phiên bản:** v2.4.2  
**Mục tiêu:**
1. Mở rộng tính năng chọn kích thước cho Vỏ thẻ Silicon Dẻo trên Bảng tính giá (`price_calculator.html`).
2. Tách biệt bộ ảnh demo cho Vỏ Silicon (Dọc / Ngang) và Vỏ Nhựa ABS (Dọc / Ngang).
3. Tối ưu hóa toàn diện giao diện Quản trị Admin Ảnh Demo (`/admin/demo-images`) theo hướng tinh gọn, phân tab thông minh và hỗ trợ tải ảnh 1 chạm (1-click upload).

---

## 1. TỔNG QUAN LUỒNG NGHIỆP VỤ BẢNG TÍNH GIÁ (STOREFRONT)

### 1.1. Quy tắc hiển thị kích thước vỏ thẻ
- **Khi chọn Vỏ Silicon Dẻo (`holderType === 'silicone'`):**
  - Tự động hiển thị khối chọn kích thước (Bước 2.1) ngay dưới bước chọn chất liệu.
  - Các kích thước được đồng bộ tương ứng với khổ thẻ nhựa PVC lồng bên trong:
    1. **Khổ `5.4 × 8.6 cm` (Chuẩn thẻ ATM):** Đồng giá **3.000 đ/cái**.
    2. **Khổ `7.0 × 11.0 cm` (Khổ nhỡ sự kiện, hội thảo):** Đồng giá **5.000 đ/cái**.
    3. **Khổ `9.0 × 12.0 cm` (Khổ lớn đại biểu, ban tổ chức):** Đồng giá **7.000 đ/cái**.
- **Khi chọn Vỏ Nhựa ABS Trơn hoặc Vỏ ABS In UV:**
  - Tự động ẩn hoàn toàn khối chọn kích thước vì vỏ nhựa ABS chỉ có duy nhất 1 kích thước tiêu chuẩn đựng vừa thẻ ATM 5.4 × 8.6 cm.

### 1.2. Cơ chế hiển thị ảnh demo 1 ảnh duy nhất (Dynamic Preview)
Hệ thống hiển thị đúng duy nhất 1 ảnh demo trực quan ở cột bên phải theo ma trận lựa chọn:
- **Khách chọn Vỏ Silicon Dẻo:**
  - Dáng đứng dọc $\rightarrow$ Hiển thị ảnh `demo_vo_silicone_doc.jpg` (Vỏ silicon dẻo dáng dọc, có khóa zip chống nước).
  - Dáng nằm ngang $\rightarrow$ Hiển thị ảnh `demo_vo_silicone_ngang.jpg` (Vỏ silicon dẻo dáng ngang, có khóa zip chống nước).
- **Khách chọn Vỏ Nhựa ABS Trơn hoặc In UV:**
  - Dáng đứng dọc $\rightarrow$ Hiển thị ảnh `demo_vo_the_dang_doc.jpg` (Vỏ nhựa ABS cứng cáp dáng đứng dọc).
  - Dáng nằm ngang $\rightarrow$ Hiển thị ảnh `demo_vo_the_dang_ngang.jpg` (Vỏ nhựa ABS cứng cáp dáng nằm ngang).

---

## 2. NÂNG CẤP GIAO DIỆN QUẢN TRỊ ADMIN (`/admin/demo-images`)

Nhằm khắc phục tình trạng giao diện trước đây bị rườm rà và rối mắt, trang quản trị được thiết kế lại toàn diện:
1. **Phân Tab danh mục rõ ràng:**
   - **Tab 1: Thẻ Nhựa PVC:** Quản lý 3 mẫu gia công đục lỗ (*Không đục lỗ*, *Lỗ Oval con nhộng*, *Lỗ tròn 5mm*).
   - **Tab 2: Vỏ Đựng Thẻ:** Phân thành 2 nhóm độc lập:
     - *Nhóm A: Vỏ Silicon Dẻo (Khóa zip chống nước)* gồm 2 mẫu (Dọc & Ngang).
     - *Nhóm B: Vỏ Nhựa ABS (Cứng cáp chuẩn ATM)* gồm 2 mẫu (Dọc & Ngang).
2. **Cơ chế 1-Click Upload thông minh:**
   - Nút to nổi bật `[ 📁 Đổi Ảnh Mới ]`: Quản trị viên chỉ cần bấm chọn tệp ảnh từ máy tính, ảnh sẽ được tự động tải lên và lưu vào hệ thống qua AJAX mà không cần thêm thao tác phụ.
   - Hiển thị Toast thông báo trạng thái nổi góc màn hình tức thì.
3. **Thu gọn các trường cấu hình chữ (KISS Principle):**
   - Tiêu đề và nhãn badge được đưa vào khối Accordion `[ ⚙️ Tùy chỉnh chữ hiển thị ]`, mặc định ẩn để giữ màn hình thông thoáng, chỉ tập trung vào hình ảnh trực quan.

---

## 3. DANH SÁCH TÀI NGUYÊN VÀ FILE THAY ĐỔI

1. **Bộ ảnh Demo 3D AI chân thực:**
   - `frontend/storefront/static/images/demo/demo_vo_silicone_doc.jpg` (Vỏ silicon dọc)
   - `frontend/storefront/static/images/demo/demo_vo_silicone_ngang.jpg` (Vỏ silicon ngang)
2. **Backend Services & API:**
   - `backend/services/data_service.py`: Mở rộng `calculate_holder_price` tính giá theo 3 kích thước của vỏ silicon; cập nhật `DEFAULT_DEMO_IMAGES`.
   - `backend/admin/routes.py`: Hỗ trợ upload và cập nhật các trường mới cho vỏ silicon dọc và ngang.
3. **Frontend Templates:**
   - `frontend/admin/templates/demo_images.html`: Tối ưu giao diện theo Tab và upload trực tiếp.
   - `frontend/storefront/templates/components/price_calculator.html`: Thêm khối `#holderSizeBlock`, hỗ trợ hàm `setHolderSize()`, phân luồng hiển thị ảnh preview.

---

## 4. KẾT QUẢ KIỂM THỬ THỰC TẾ (AUTOMATED VERIFICATION)

| Kịch Bản Kiểm Thử | Dữ Liệu Đầu Vào | Kết Quả Mong Đợi | Kết Quả Thực Tế | Trạng Thái |
| :--- | :--- | :--- | :--- | :--- |
| **Giá Vỏ Silicon 5.4×8.6** | Số lượng: 100, Type: Silicone, Size: 5.4x8.6 | Đơn giá: 3.000 đ, Tổng: 300.000 đ | 3.000 đ / 300.000 đ | **PASS** |
| **Giá Vỏ Silicon 7×11** | Số lượng: 100, Type: Silicone, Size: 7x11 | Đơn giá: 5.000 đ, Tổng: 500.000 đ | 5.000 đ / 500.000 đ | **PASS** |
| **Giá Vỏ Silicon 9×12** | Số lượng: 100, Type: Silicone, Size: 9x12 | Đơn giá: 7.000 đ, Tổng: 700.000 đ | 7.000 đ / 700.000 đ | **PASS** |
| **Giá Vỏ ABS Trơn** | Số lượng: 100, Type: Plain | Đơn giá: 7.000 đ, Tổng: 700.000 đ | 7.000 đ / 700.000 đ | **PASS** |
| **API `/api/calculate-price`** | POST Holder Silicone 50 cái khổ 7x11 | Đơn giá 5.000 đ, Tổng 250.000 đ | 5.000 đ / 250.000 đ | **PASS** |
| **Trang Admin `/admin/demo-images`** | GET Request | HTTP 200 OK, đầy đủ 2 Tab | HTTP 200 OK | **PASS** |
