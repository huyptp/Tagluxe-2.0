# Tài Liệu Đặc Tả Kỹ Thuật: Hệ Thống Quản Lý Phụ Kiện & Vỏ Thẻ TagLuxe

- **Dự án**: TagLuxe Storefront & Admin Control Panel
- **Ngày triển khai**: 08-10-2026
- **Trạng thái**: Đã nghiệm thu & Hoạt động thực tế (Production Ready)

---

## 1. Tổng Quan Mục Tiêu
Hệ thống cho phép Quản trị viên trực tiếp quản lý danh mục phụ kiện và các loại vỏ đựng thẻ trong trang quản trị (**Admin Control Panel**), bao gồm:
- **Tải lên & thay đổi hình ảnh thực tế** trực tiếp từ máy tính (hỗ trợ JPG, PNG, WEBP tối đa 10MB).
- **Tùy chỉnh đơn giá cộng thêm** (ví dụ: vỏ 3k, vỏ 7k, phụ kiện +2.5k...).
- **Cập nhật tên gọi & mô tả công dụng**.
- **Bật/tắt hiển thị linh hoạt** khi hết hàng hoặc ngừng kinh doanh.
- **Tự động đồng bộ ra ngoài Storefront**: Khi khách hàng bấm chọn vào bất kỳ tùy chọn nào trên Bảng tính giá ngoài website, khung xem trước (Live Preview) sẽ lập tức hiển thị đúng hình ảnh thực tế được quản trị viên tải lên.

---

## 2. Danh Mục Phụ Kiện Quản Lý Ban Đầu (9 Món)

### Nhóm 1: Phụ Kiện Dây Đeo Thẻ (`lanyard_acc`)
1. **Khóa an toàn sau gáy** (`breakaway`) — Đơn giá: `+2.500 đ`
   - *Công dụng*: Tự tách rời khi bị kéo căng mạnh, giúp bảo vệ an toàn cho người đeo không bị thắt cổ khi vướng máy móc.
2. **Khóa phụ tháo rời nhanh** (`quick_release`) — Đơn giá: `+2.500 đ`
   - *Công dụng*: Khóa bấm tháo rời nhanh tiện lợi, dễ dàng tháo riêng thẻ chấm công hoặc chìa khóa để quẹt mà không cần tháo cả dây qua đầu.
3. **Cục thắt thu độ dài dây** (`stopper`) — Đơn giá: `+2.500 đ`
   - *Công dụng*: Cục thắt chặn hình tròn nhỏ gọn, trượt lên xuống để thu gọn độ dài dây đeo vừa vặn với từng vóc dáng người dùng.
4. **Tăng đơ tăng giảm độ dài** (`adjuster`) — Đơn giá: `+2.500 đ`
   - *Công dụng*: Khóa tăng đơ 3 chấu cao cấp, tùy chỉnh nới dài hoặc rút ngắn chiều dài dây linh hoạt và chắc chắn.
5. **Móc kim loại đen mờ** (`black_hook`) — Đơn giá: `+2.500 đ`
   - *Công dụng*: Móc càng cua kim loại cao cấp phủ sơn tĩnh điện đen mờ, chống xước, tạo điểm nhấn cá tính và hiện đại.

### Nhóm 2: Kiểu Dáng Vỏ Đựng Thẻ (`holder_orientation`)
6. **Vỏ thẻ dáng đứng (Vertical)** (`holder_vertical`) — Đơn giá: `0 đ (Tiêu chuẩn)`
   - *Công dụng*: Kiểu dáng đứng dọc truyền thống, phù hợp với thẻ nhân viên và thẻ học sinh - sinh viên.
7. **Vỏ thẻ dáng ngang (Horizontal)** (`holder_horizontal`) — Đơn giá: `0 đ (Tiêu chuẩn)`
   - *Công dụng*: Kiểu dáng ngang sang trọng, bề ngang rộng rãi phù hợp nhận diện thương hiệu công ty.

### Nhóm 3: Chất Liệu & Quy Cách Vỏ Thẻ (`holder_material`)
8. **Vỏ silicon dẻo trong suốt (Vỏ 3k)** (`holder_silicone`) — Đơn giá: `+3.000 đ`
   - *Công dụng*: Chất liệu silicon mềm dẻo, chống nước và chống bám bụi bẩn tối ưu, giá thành kinh tế.
9. **Vỏ nhựa ABS trơn không in (Vỏ 7k)** (`holder_plain`) — Đơn giá: `+7.000 đ`
   - *Công dụng*: Nhựa ABS cứng cáp nhiều màu sắc (xanh, đỏ, đen, xám, trắng...), chống va đập, bảo vệ thẻ tối ưu.

---

## 3. Cấu Trúc Cơ Sở Dữ Liệu (Database Model)
Bảng `accessories` được định nghĩa trong `backend/models.py`:
- `id` (VARCHAR 50, Primary Key): Mã định danh duy nhất của phụ kiện.
- `name` (VARCHAR 255): Tên hiển thị của phụ kiện.
- `category` (VARCHAR 50): Phân loại (`lanyard_acc`, `holder_orientation`, `holder_material`).
- `price` (INTEGER): Đơn giá cộng thêm (VNĐ).
- `image` (VARCHAR 255): Đường dẫn tương đối hoặc tệp tải lên (`/static/uploads/acc_...`).
- `description` (TEXT): Mô tả công dụng chi tiết.
- `title` (VARCHAR 255): Tiêu đề mở rộng khi phóng to xem chi tiết.
- `sort_order` (INTEGER): Thứ tự sắp xếp hiển thị.
- `visible` (BOOLEAN): Trạng thái hiển thị (`True` = đang hiện, `False` = ẩn).

---

## 4. Các Tuyến Quản Trị & API (Endpoints)

### A. Quản trị Admin (`backend/admin/routes.py`)
- `GET /admin/accessories`: Trang danh sách quản lý giao diện trực quan, bảng phân loại theo tabs, thẻ KPI thống kê.
- `POST /admin/accessories/edit/<acc_id>`: Cập nhật tên, giá, mô tả, trạng thái hiển thị và tải ảnh mới.
- `POST /admin/accessories/upload/<acc_id>`: Tải lên và thay đổi ảnh nhanh qua AJAX.
- *Bảo mật*: Yêu cầu đăng nhập quản trị (`@login_required`), chống tấn công CSRF (`validate_csrf()`), kiểm tra định dạng ảnh bằng Magic Bytes (`is_valid_image_file`), ghi vết nhật ký kiểm toán (`AuditLog`).

### B. API Khách Hàng Storefront (`backend/api/routes.py`)
- `GET /api/accessories`: Cung cấp danh mục phụ kiện và vỏ thẻ theo thời gian thực cho Bảng tính giá.

---

## 5. Hướng Dẫn Sử Dụng Dành Cho Quản Trị Viên

1. **Đăng nhập hệ thống Admin**:
   - Truy cập: `http://127.0.0.1:5000/admin/login` (hoặc tên miền chính thức).
   - Đăng nhập bằng tài khoản quản trị.
2. **Vào mục "Phụ kiện & Vỏ thẻ"**:
   - Bấm vào tab menu **"Phụ kiện & Vỏ thẻ"** trên thanh điều hướng đầu trang.
3. **Thay đổi hình ảnh**:
   - Bấm nút **[Đổi ảnh]** hoặc bấm trực tiếp vào ảnh đại diện của phụ kiện.
   - Hộp thoại cập nhật sẽ xuất hiện. Bấm vào ô chọn ảnh để tải tệp từ máy tính (khuyến nghị ảnh vuông 1:1, độ phân giải cao).
   - Kiểm tra ảnh xem trước mới -> Bấm **"Lưu thay đổi & Cập nhật ảnh"**.
4. **Thay đổi giá bán & Trạng thái**:
   - Bấm nút **[Sửa]** -> Nhập đơn giá mới (ví dụ từ 3.000 đ thành 4.000 đ).
   - Bật hoặc tắt công tắc **"Bật hiển thị"** để ẩn phụ kiện nếu tạm thời hết hàng ngoài kho.
5. **Kiểm tra ngoài trang chủ**:
   - Mở website ngoài trang chủ (`/`) -> Trong Bảng tính giá, bấm chọn vào phụ kiện vừa đổi ảnh để xem kết quả hiển thị tức thì.
