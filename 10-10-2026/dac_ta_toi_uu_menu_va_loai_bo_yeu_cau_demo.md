# ĐẶC TẢ KỸ THUẬT & BẢN THIẾT KẾ MOCKUP: LOẠI BỎ YÊU CẦU DEMO & TỐI ƯU ĐƯỜNG DẪN MENU

**Dự án:** TagLuxe 2.0 — Website Bán Sỉ & Sản Xuất Dây Đeo Thẻ, Thẻ Nhựa PVC & Phụ Kiện  
**Ngày thực hiện:** 10/10/2026  
**Trạng thái:** Đang chờ người dùng phê duyệt Mockup (Rule 12)  

---

## 1. MỤC TIÊU & TỔNG QUAN

Theo phản hồi của người dùng:
1. **Loại bỏ phần "Yêu cầu Demo" trong trang Admin**: Mục này không còn cần thiết vì khách hàng hiện tại gửi yêu cầu trực tiếp qua Zalo hoặc Form Báo giá tự động. Việc loại bỏ giúp thanh điều hướng Admin gọn gàng, tập trung vào các chức năng vận hành cốt lõi.
2. **Tối ưu hóa đường dẫn trang web**: Tinh chỉnh và chuẩn hóa toàn bộ các liên kết điều hướng (Header Navigation, Footer Links trên Storefront và Admin Navigation Bar) sao cho văn bản khớp 100% với 3 tiêu đề sản phẩm mới đã chuẩn hóa.

---

## 2. BẢN THIẾT KẾ MOCKUP GIAO DIỆN ADMIN (TRƯỚC & SAU)

### 2.1. Thanh Điều Hướng Admin Trước Đây (Bị thừa & dài dòng)
```
+----------------------------------------------------------------------------------------------------------------------+
| [TAGLUXE ADMIN]  📦 Sản phẩm  |  🧮 Báo giá  |  [📥 Yêu cầu Demo (THỪA)]  |  📑 Bảng giá & Phụ kiện  |  🖼️ Ảnh Demo  |  🚪 Đăng xuất |
+----------------------------------------------------------------------------------------------------------------------+
```

### 2.2. Thanh Điều Hướng Admin Đề Xuất Mới (Gọn gàng, Chuyên nghiệp)
```
+----------------------------------------------------------------------------------------------------------------------+
| [TAGLUXE ADMIN]  📦 Sản phẩm  |  🧮 Báo giá  |  📑 Bảng giá & Phụ kiện  |  🖼️ Ảnh Demo Báo Giá  |  🚩 Banner Chiến Dịch  |  🚪 Đăng xuất |
+----------------------------------------------------------------------------------------------------------------------+
```

> **Cơ chế an toàn kỹ thuật**:  
> - Loại bỏ thẻ link `Yêu cầu Demo` khỏi [base.html](file:///C:/Users/dinhq/.gemini/antigravity/worktrees/TAGLUXE/continue_developing_tagluxe/frontend/admin/templates/base.html).
> - Giữ nguyên bảng dữ liệu `DemoRequest` trong SQLite database để không gây mất mát dữ liệu lịch sử.
> - Thiết lập chuyển hướng mềm (HTTP 302 Redirect) từ `/admin/requests` về `/admin/quotes` để bảo vệ các bookmark cũ.

---

## 3. BẢN THIẾT KẾ MOCKUP ĐƯỜNG DẪN STOREFRONT (HEADER & FOOTER)

### 3.1. Header Main Navigation (`base.html`)
```
+---------------------------------------------------------------------------------------------------------------------+
| [TAGLUXE LOGO]      Trang chủ | Dây đeo thẻ | Thẻ nhựa PVC | Vỏ đựng thẻ | Báo giá | Quy trình | FAQ | [ 💬 Liên hệ ] |
+---------------------------------------------------------------------------------------------------------------------+
```

### 3.2. Footer Product Links (Tối ưu hóa văn bản chuẩn 3 tiêu đề mới)
```
[CHÂN TRANG - CỘT SẢN PHẨM]
------------------------------------------------------------
Trước đây:
  - 🏠 Trang chủ
  - 🏷️ In dây đeo thẻ theo yêu cầu
  - 💳 In thẻ nhựa PVC
  - 📦 Vỏ đựng thẻ (Card holder)
  - 🧮 Bảng tính báo giá tự động
  - 📋 Quy trình & Duyệt mẫu
  - ❓ Câu hỏi thường gặp

Sau khi tối ưu (Chuẩn hóa 100%):
  - 🏠 Trang chủ
  - 🏷️ Dây đeo thẻ in theo yêu cầu
  - 💳 Thẻ nhựa PVC in theo yêu cầu
  - 📦 Vỏ đựng thẻ (Card holder) in theo yêu cầu
  - 🧮 Bảng tính báo giá tự động
  - 📋 Quy trình & Duyệt mẫu
  - ❓ Câu hỏi thường gặp
```

---

## 4. DANH SÁCH FILE THAY ĐỔI

1. `frontend/admin/templates/base.html` & `templates/admin/base.html`: Xóa mục `Yêu cầu Demo`, sắp xếp menu hợp lý.
2. `backend/admin/routes.py`: Thêm chuyển hướng `/admin/requests` -> `/admin/quotes`.
3. `frontend/storefront/templates/base.html` & `templates/base.html`: Chuẩn hóa anchor links và footer links.
4. Đồng bộ toàn bộ sang kho chính `D:\Antigravity\TAGLUXE`.
