# TÀI LIỆU ĐẶC TẢ KỸ THUẬT & HƯỚNG DẪN VẬN HÀNH
## BẢNG SETUP GIÁ BÁN THEO SỐ LƯỢNG & QUẢN LÝ THÊM MỚI PHỤ KIỆN
**Dự án:** TagLuxe - Xưởng Sản Xuất Dây Đeo Thẻ & Thẻ Nhựa Cao Cấp  
**Ngày lập:** 08/10/2026  
**Trạng thái:** Đã được Người dùng duyệt thiết kế Mockup UI  

---

### 1. Mục Tiêu Nghiệp Vụ
1. **Quản lý biến động chi phí nguyên vật liệu:** Cho phép Quản trị viên (Admin) trực tiếp điều chỉnh bảng giá sỉ/lẻ của từng dòng sản phẩm theo các bậc số lượng (Dây đeo thẻ, Thẻ nhựa PVC, Vỏ đựng thẻ).
2. **Linh hoạt mở rộng danh mục phụ kiện:** Khi xưởng nhập thêm mẫu phụ kiện mới (móc khóa kim loại, khóa an toàn, dây nối nhanh, vỏ thẻ mẫu mới...), Admin có thể bấm nút **"+ Thêm Mẫu Phụ Kiện Mới"** để đưa lên hệ thống ngay mà không cần can thiệp mã nguồn.
3. **Đồng bộ tự động ra ngoài Website:** Khi Admin lưu biểu giá mới hoặc thêm phụ kiện mới, công cụ tính giá nhanh ngoài trang chủ (`price_calculator.html`) sẽ tự động lấy dữ liệu mới từ CSDL để tính tổng tiền chính xác 100%.

---

### 2. Cấu Trúc Giao Diện Quản Trị (Admin UI)
Được tích hợp tập trung tại trang **"Bảng giá & Phụ kiện"** (`/admin/accessories`):
- **Tab 1: Biểu Giá Theo Số Lượng (Volume-Tiered Matrix)**:
  - Bảng giá Dây đeo thẻ (Lanyard): 13 bậc số lượng chuẩn ngành xưởng (10–21, 22–31, 32–45, 46–70, 71–120, 121–200, 201–320, 321–420, 421–530, 531–710, 711–1000, 1001–2000, 2000+).
  - Bảng giá Thẻ nhựa PVC (5.4x8.6cm, 7x11cm, 9x12cm) theo các mốc số lượng.
  - Bảng giá Vỏ thẻ các loại (nhựa dẻo, mica, da simili, nắp trượt...).
  - Mỗi hàng có ô nhập giá mới, hiển thị giá cũ và nút bấm **"Lưu Toàn Bộ Biểu Giá Mới"**.
- **Tab 2: Quản Lý Phụ Kiện & Vỏ Thẻ**:
  - Nút **"+ Thêm Mẫu Phụ Kiện Mới"** nổi bật.
  - Danh sách bảng các phụ kiện hiện có kèm ảnh xem trước, tên, mã code, danh mục, đơn giá cộng thêm, nút bật/tắt hiển thị, nút sửa và nút đổi ảnh.
- **Modal Popup "+ Thêm Mẫu Phụ Kiện Mới"**:
  - Tên phụ kiện (bắt buộc).
  - Danh mục phân loại: Phụ kiện dây đeo (`lanyard_acc`), Kiểu dáng vỏ thẻ (`holder_orientation`), Chất liệu vỏ thẻ (`holder_material`).
  - Đơn giá cộng thêm (VNĐ) (bắt buộc).
  - Tải ảnh minh họa từ máy tính (hỗ trợ JPG, PNG, WEBP, tự động kiểm tra magic header an toàn).
  - Mô tả / phụ đề ngắn gọn.

---

### 3. Thiết Kế Cơ Sở Dữ Liệu & Backend API
- **Model `PriceTier` (bảng `price_tiers`)**:
  - `id`: Khóa chính.
  - `category`: `lanyard`, `pvc`, `pvc_5.4x8.6`, `pvc_7x11`, `pvc_9x12`, `holder`, `holder_plain`, `holder_silicone`, `combo`.
  - `min_qty`, `max_qty`: Khoảng số lượng áp dụng.
  - `unit_price`: Đơn giá xuất xưởng tương ứng (VNĐ).
- **Model `Accessory` (bảng `accessories`)**:
  - `id`: Mã định danh duy nhất (sinh tự động dạng slug/prefix).
  - `name`: Tên phụ kiện.
  - `category`: Nhóm phụ kiện.
  - `price`: Đơn giá cộng thêm (VNĐ).
  - `image`: Đường dẫn file ảnh upload (`/static/uploads/...`).
  - `description`: Mô tả chi tiết.
  - `visible`: Trạng thái hiển thị (True/False).
- **Các API Endpoint Quản Trị**:
  - `GET /admin/accessories`: Hiển thị trang quản trị trung tâm với 2 Tab dữ liệu.
  - `POST /admin/pricing/update`: Nhận dữ liệu ma trận giá, cập nhật vào bảng `price_tiers`.
  - `POST /admin/accessories/add`: Nhận multipart/form-data thêm phụ kiện mới và upload ảnh.
  - `POST /admin/accessories/edit/<acc_id>`: Cập nhật thông tin phụ kiện.
  - `POST /admin/accessories/toggle-visibility/<acc_id>`: Bật/tắt hiển thị phụ kiện trên website.

---

### 4. Kiểm Thử & Nghiệm Thu
1. Thử thay đổi đơn giá bậc `10–21` dây đeo và bậc `100–200` thẻ PVC trong trang Admin.
2. Kiểm tra log và database xác nhận giá trị mới đã được lưu.
3. Ra trang chủ chạy công cụ tính giá với số lượng tương ứng, đối soát kết quả tính toán đảm bảo trùng khớp 100%.
4. Thử thêm 1 phụ kiện mới có ảnh, xác nhận phụ kiện xuất hiện đầy đủ trong trang quản trị và trong danh mục phụ kiện của web.
