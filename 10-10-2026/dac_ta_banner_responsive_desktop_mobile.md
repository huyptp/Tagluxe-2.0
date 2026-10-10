# ĐẶC TẢ KỸ THUẬT & HƯỚNG DẪN QUẢN TRỊ
## TÍNH NĂNG TẢI 2 BANNER CHIẾN DỊCH RIÊNG BIỆT CHO DESKTOP & MOBILE (RESPONSIVE)

---

- **Dự án**: TAGLUXE B2B E-Commerce Platform
- **Ngày thực hiện**: 10-10-2026
- **Trạng thái**: Đã triển khai & Kiểm thử thành công 100%
- **Môi trường**: Worktree & Main Repository (`D:\Antigravity\TAGLUXE`)
- **Lưu ý triển khai**: Lưu trữ cục bộ hoàn toàn (Local), chỉ đẩy lên GitHub khi có xác nhận trực tiếp từ người dùng.

---

### 1. BỐI CẢNH VÀ MỤC TIÊU NÂNG CẤP

#### 1.1. Bối cảnh
Trước đây, hệ thống chỉ hỗ trợ tải lên 1 file ảnh banner duy nhất cho mọi thiết bị. Khi dùng chung 1 ảnh:
- Nếu thiết kế banner theo chiều ngang (16:9) để hiển thị đẹp trên Laptop/Máy tính, khi hiển thị trên màn hình dọc của Smartphone (Mobile), banner sẽ bị thu quá nhỏ, chữ li ti và khó đọc.
- Ngược lại, nếu thiết kế banner theo chiều dọc (4:5) cho Mobile, khi mở trên Laptop thì banner lại quá cao, che khuất toàn bộ màn hình khiến trải nghiệm người dùng bị giảm sút.

#### 1.2. Mục tiêu đạt được
1. **Trang Quản trị Admin (`/admin/campaign-banner`)**:
   - Cho phép quản trị viên tải lên **2 ảnh banner riêng biệt**:
     - 1 ảnh tối ưu cho **Màn hình Máy tính & Laptop (Desktop)**.
     - 1 ảnh tối ưu cho **Màn hình Điện thoại Smartphone (Mobile)**.
   - Ghi rõ thông số kỹ thuật, tỉ lệ chuẩn và kích thước pixel khuyến nghị ngay dưới từng ô tải ảnh để tiện cho khâu thiết kế đồ họa.
   - Hỗ trợ công tắc Bật/Tắt chung, nút xóa riêng từng banner và nút xóa toàn bộ.
   - Live Preview thông minh: Hỗ trợ 2 Tab xem trước **[ 💻 Xem Desktop (16:9) ]** và **[ 📱 Xem Mobile (4:5) ]** mô phỏng chính xác khung hiển thị thực tế.
2. **Trải nghiệm Storefront**:
   - Sử dụng thẻ chuẩn HTML5 `<picture>` và Media Queries: Trình duyệt tự động nhận diện thiết bị của người dùng để nạp đúng file banner tối ưu nhất mà không gây lãng phí băng thông 3G/4G.
   - **Ràng buộc an toàn tuyệt đối**: Nếu chưa có bất kỳ ảnh nào tải lên hoặc sau khi quản trị viên xóa ảnh, popup banner **TUYỆT ĐỐI KHÔNG HIỂN THỊ** trên website.

---

### 2. THÔNG SỐ KỸ THUẬT VÀ TỈ LỆ CHUẨN

*(Dữ liệu chuẩn hóa dựa trên khuyến nghị từ [OptinMonster](https://optinmonster.com) & [Sleeknote](https://sleeknote.com)):*

| Loại thiết bị | Tỉ lệ khuyến nghị (Aspect Ratio) | Kích thước xuất file (Khuyên dùng) | Kích thước tối thiểu | Dung lượng tối ưu | Định dạng hỗ trợ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **💻 Máy tính & Laptop**<br>*(Màn hình ngang $\ge 768px$)* | **16:9** *(Chuẩn)*<br>hoặc **3:2** | **1200 × 675 px** *(16:9)*<br>hoặc **1200 × 800 px** *(3:2)* | 800 × 450 px | $\le 350$ KB | JPG, PNG, WEBP |
| **📱 Điện thoại (Mobile)**<br>*(Màn hình dọc $< 768px$)* | **4:5** *(Dọc)*<br>hoặc **1:1** *(Vuông)* | **1080 × 1350 px** *(4:5)*<br>hoặc **1080 × 1080 px** *(1:1)* | 720 × 900 px *(4:5)*<br>hoặc 600 × 600 px *(1:1)* | $\le 250$ KB | JPG, PNG, WEBP |

---

### 3. KIẾN TRÚC DỮ LIỆU & CƠ CHẾ KỸ THUẬT

#### 3.1. Cấu trúc lưu trữ JSON (`storage/campaign_banner.json`)
```json
{
  "title": "Chương Trình Khuyến Mại",
  "image_desktop": "/static/uploads/campaign_banner_desk_xxxx.jpg",
  "image_mobile": "/static/uploads/campaign_banner_mob_yyyy.jpg",
  "image": "/static/uploads/campaign_banner_desk_xxxx.jpg",
  "enabled": true,
  "updated_at": "2026-10-10 20:45:00"
}
```

#### 3.2. Cơ chế Fallback an toàn
- Nếu quản trị viên chỉ tải ảnh Desktop: Hệ thống tự dùng ảnh này làm dự phòng cho cả Mobile.
- Nếu quản trị viên chỉ tải ảnh Mobile: Hệ thống tự dùng ảnh này làm dự phòng cho cả Desktop.
- Nếu xóa ảnh Desktop: Ảnh Mobile vẫn hoạt động bình thường trên cả 2 thiết bị.
- Nếu xóa toàn bộ: Cả 2 ảnh bị xóa sạch và cờ `enabled` tự động chuyển về `False`.

#### 3.3. Thẻ HTML5 Responsive trên Storefront
```html
<picture class="campaign-banner-picture">
    {% if campaign_banner.image_mobile %}
    <source media="(max-width: 767px)" srcset="{{ campaign_banner.image_mobile }}">
    {% endif %}
    {% if campaign_banner.image_desktop %}
    <source media="(min-width: 768px)" srcset="{{ campaign_banner.image_desktop }}">
    {% endif %}
    <img src="{{ campaign_banner.image_desktop or campaign_banner.image_mobile or campaign_banner.image }}"
         alt="{{ campaign_banner.title or 'Banner Khuyến Mại TagLuxe' }}"
         loading="eager" class="campaign-banner-img">
</picture>
```

---

### 4. DANH SÁCH FILE ĐÃ TRIỂN KHAI VÀ ĐỒNG BỘ

| STT | Tệp tin | Vai trò cập nhật |
|:---:|:---|:---|
| 1 | `backend/services/data_service.py` | Bổ sung quản lý `image_desktop`, `image_mobile`, hàm xóa theo `target` |
| 2 | `backend/admin/routes.py` | Hỗ trợ upload đồng thời `banner_image_desktop` và `banner_image_mobile`, kiểm duyệt file |
| 3 | `frontend/admin/templates/campaign_banner.html` | Giao diện quản trị 2 banner, ghi rõ tỉ lệ và kích thước, Live Preview 2 tab |
| 4 | `templates/admin/campaign_banner.html` | Đồng bộ template admin tương ứng |
| 5 | `frontend/storefront/templates/base.html` | Thêm thẻ `<picture>` đa nguồn media responsive cho popup banner |
| 6 | `templates/base.html` | Đồng bộ template storefront tương ứng |
| 7 | `10-10-2026/dac_ta_banner_responsive_desktop_mobile.md` | Tài liệu đặc tả kỹ thuật Markdown |
| 8 | `10-10-2026/dac_ta_banner_responsive_desktop_mobile.docx` | Tài liệu đặc tả kỹ thuật Microsoft Word |

---

### 5. HƯỚNG DẪN QUẢN TRỊ VIÊN SỬ DỤNG

1. Truy cập trang Admin: `http://localhost:5000/admin/campaign-banner` (hoặc bấm **Banner Chiến Dịch** trên thanh menu).
2. **Tải Banner Desktop**:
   - Nhìn vào khung **1. Banner Máy Tính & Laptop (Desktop)** (Tỉ lệ 16:9, kích thước 1200 × 675 px).
   - Bấm vào ô chọn ảnh và chọn tệp từ máy tính.
3. **Tải Banner Mobile**:
   - Nhìn vào khung **2. Banner Điện Thoại (Mobile)** (Tỉ lệ 4:5, kích thước 1080 × 1350 px).
   - Bấm vào ô chọn ảnh và chọn tệp từ máy tính.
4. Bấm tab **[ 💻 Xem Desktop ]** và **[ 📱 Xem Mobile ]** ở cột Live Preview bên phải để kiểm tra độ sắc nét và bố cục.
5. Tích chọn *"Bật hiển thị popup ngay sau khi lưu"* và bấm nút **"Lưu Cấu Hình Banner"**.
6. Khi muốn gỡ bỏ:
   - Có thể bấm nút *"Xóa ảnh Desktop"* hoặc *"Xóa ảnh Mobile"* riêng biệt; HOẶC
   - Bấm nút đỏ *"Xóa Cả 2 Banner & Tắt Popup"* để dọn sạch dữ liệu và tắt popup trên toàn website.
