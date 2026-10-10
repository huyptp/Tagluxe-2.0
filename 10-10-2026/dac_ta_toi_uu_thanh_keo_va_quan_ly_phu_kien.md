# ĐẶC TẢ KỸ THUẬT: TỐI ƯU THANH KÉO SỐ LƯỢNG & QUẢN LÝ PHỤ KIỆN THEO MỐC DÂY (TAGLUXE 2.0)

**Ngày thực hiện:** 10/10/2026  
**Dự án:** TagLuxe 2.0 — Xưởng Sản Xuất Dây Đeo Thẻ & Thẻ Nhựa Cao Cấp  
**Trạng thái:** Đã phê duyệt phương án & Mockup (Approved)  

---

## 1. TỔNG QUAN YÊU CẦU & BỐI CẢNH

### 1.1. Tối ưu thanh kéo số lượng tại Công cụ Báo Giá (Price Calculator)
* **Hiện trạng lỗi**:
  * Các mốc hiển thị dưới thanh kéo được chia đều theo tỷ lệ phần trăm: `10` (0%), `100` (25%), `500` (50%), `1.000` (75%), `3.000+` (100%).
  * Tuy nhiên, thẻ trượt HTML `<input type="range" min="10" max="3000">` lại phân bố đều theo số học tuyến tính (Linear).
  * Do đó, khi khách hàng kéo núm trượt đến ngay vạch `100` (vị trí 25%), giá trị tính toán lại nhảy lên `755`! Khi kéo đến giữa thanh tại vạch `500`, giá trị lại nhảy lên `1.505`!
  * Ngoài ra, dòng hiển thị số lượng và tổng tiền trên Bảng dự toán chi phí bên phải bị độ trễ (debounce mạng) khiến con số hiển thị không khớp theo thời gian thực.
* **Giải pháp khắc phục**:
  * Chuyển đổi thanh trượt sang thuật toán **Piecewise Non-linear Curve Mapping (Ánh xạ 4 phân khúc)** khớp chuẩn xác 100% với các vạch mốc `10`, `100`, `500`, `1.000`, `3.000`.
  * Cập nhật thời gian thực **Zero-Lag (0ms)**: Khi ngón tay/chuột vừa di chuyển thanh kéo, dòng hiển thị số lượng trên Bảng dự toán chi phí cập nhật ngay lập tức.
  * Đồng bộ hai chiều trơn tru giữa Ô gõ trực tiếp (`qtyDirectInput`), Thanh kéo (`qtySliderInput`), Nút bấm tăng/giảm (`[-10]`, `[+10]`, `[+50]`) và Bảng dự toán chi phí (`ticketQty`).

### 1.2. Quản lý phụ kiện kích hoạt theo số lượng dây tối thiểu trong Admin
* **Mục tiêu nghiệp vụ**:
  * Một số loại phụ kiện gia công phức tạp (hoặc phụ kiện cao cấp như móc khóa sơn đen mờ, tăng đơ, khóa đặc biệt) xưởng chỉ nhận làm khi đơn đạt số lượng dây tối thiểu cụ thể (ví dụ: từ 50 hoặc 100 dây).
  * Cung cấp tùy chọn cấu hình trực quan trong trang Admin (`/admin/accessories`) để người quản trị chủ động cài đặt mốc số lượng này cho từng phụ kiện.
  * Tại trang Storefront: Nếu số lượng dây khách chọn chưa đạt mốc yêu cầu của phụ kiện, phụ kiện đó sẽ hiển thị trạng thái khóa (`🔒 Chỉ từ X dây`), không cho phép chọn. Nếu khách đã chọn mà giảm số lượng xuống dưới mốc, hệ thống tự động bỏ chọn phụ kiện và tính lại giá chính xác.

---

## 2. THIẾT KẾ KIẾN TRÚC & DỮ LIỆU

### 2.1. CSDL SQLite & Model `Accessory` (`backend/models.py`)
* Bổ sung trường:
  * `min_quantity = db.Column(db.Integer, nullable=False, default=0)` (hoặc quy định 0 = không giới hạn, áp dụng cho mọi đơn từ 10 dây).
* Tự động di chuyển lược đồ CSDL thông qua migration an toàn trong `backend/migrations.py` (`ALTER TABLE accessories ADD COLUMN min_quantity INTEGER DEFAULT 0`).

### 2.2. Giao diện Quản trị (`frontend/admin/templates/accessories.html`)
* Bảng danh sách phụ kiện: Thêm cột hiển thị mốc `SL Dây Tối Thiểu` (ví dụ: `Tự do (≥10)` hoặc `🔒 Từ 50 dây`).
* Modal Thêm & Sửa phụ kiện: Thêm ô nhập số `SL dây tối thiểu để chọn (dây)` với chú thích rõ ràng.

### 2.3. Công cụ tính giá Storefront (`frontend/storefront/templates/components/price_calculator.html`)
* Thuật toán ánh xạ thanh trượt:
  * Range: `0` đến `1000` điểm chia.
  * Phân khúc 1 [0 - 250]: `10 -> 100` (bước nhảy 5).
  * Phân khúc 2 [250 - 500]: `100 -> 500` (bước nhảy 25).
  * Phân khúc 3 [500 - 750]: `500 -> 1.000` (bước nhảy 50).
  * Phân khúc 4 [750 - 1000]: `1.000 -> 3.000` (bước nhảy 100).
* Hiển thị trạng thái phụ kiện khóa/mở khóa linh hoạt theo `state.qty`.

### 2.4. Tối ưu hóa Micro-Interactions Desktop (`price_calculator.html`)
* **Slider Dynamic Fill Gradient**:
  * Thanh trượt hiển thị dải màu tiến trình (`linear-gradient`) cập nhật tức thời theo ngón tay/chuột kéo: phần đã kéo hiển thị màu đen navy sang trọng (`#0f172a`), phần còn lại màu xám thanh lịch (`#e2e8f0`).
  * Núm trượt (Slider Thumb) hỗ trợ hiệu ứng phóng to viền bóng mịn (`transform: scale(1.2)` khi hover, `scale(1.28)` kèm con trỏ `grabbing` khi kéo).
* **Nút tăng giảm Stepper (`[-10]`, `[+10]`, `[+50]`)**:
  * Bổ sung hiệu ứng phản hồi nhấn chuột (`active: transform: scale(0.92)`), tăng cảm giác chân thực khi bấm liên tục.
* **Các thẻ lựa chọn quy cách (`.opt-card`, `.addon-toggle-card`)**:
  * Hiệu ứng nâng nhẹ (`translateY(-2px)`) kèm bóng đổ mượt mà khi di chuột.
  * Hiệu ứng viền phát sáng (Ring glow: `box-shadow: 0 0 0 1px #0f172a`) khi được chọn, tạo điểm nhấn cao cấp theo phong cách Minimalist Luxury.
* **Các nút chuyển đổi Tab (`.cat-tab-btn`, `.calc-ptab-btn`)**:
  * Tinh chỉnh chuyển động chuyển tab bằng đường cong gia tốc `cubic-bezier(0.4, 0, 0.2, 1)`, nút active có bóng đổ nổi bật.
* **Nút bấm gửi yêu cầu báo giá (`.btn-corporate-submit`)**:
  * Hiệu ứng nhấc nhẹ và đổ bóng sâu khi rê chuột (`translateY(-2px)`), phản hồi bấm chắc tay (`scale(0.98)`).

---

## 3. KẾ HOẠCH TRIỂN KHAI CHI TIẾT
1. Tạo migration CSDL an toàn cho bảng `accessories`.
2. Cập nhật Model `Accessory`, Service `data_service.py` và Controller `admin/routes.py`.
3. Cập nhật giao diện Admin `accessories.html` (Modal + Bảng danh sách).
4. Tối ưu thanh kéo và logic khóa phụ kiện trong `price_calculator.html`.
5. Tinh chỉnh toàn diện bộ hiệu ứng micro-interactions trên Desktop cho Bảng tính giá.
6. Kiểm định thực tế trên server cục bộ và xuất báo cáo hoàn tất.
