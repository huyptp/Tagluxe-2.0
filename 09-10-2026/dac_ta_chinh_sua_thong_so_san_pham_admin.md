# ĐẶC TẢ KỸ THUẬT: CẤU HÌNH THÔNG SỐ VÀ MÔ TẢ 3 DÒNG SẢN PHẨM TRONG ADMIN

**Dự án**: TagLuxe E-Commerce & B2B  
**Ngày thực hiện**: 09-10-2026  
**Trạng thái**: Đã phê duyệt phương án & tên file (Approved)  

---

## 1. MỤC TIÊU & ĐỐI TƯỢNG NGHIỆP VỤ

### 1.1. Hiện trạng trước khi nâng cấp
- Các thông số kỹ thuật (bản rộng, chất liệu, tiêu chuẩn in, phụ kiện, thời gian sản xuất, nhận in từ, hóa đơn VAT...), nhãn Badge (`DÂY ĐEO THẺ IN THEO YÊU CẦU`, `THẺ NHỰA PVC CHUẨN ISO 7810`, `VỎ ĐỰNG THẺ (CARD HOLDER) CAO CẤP`) trên trang chi tiết sản phẩm (`/product/<id>`) phần lớn đang bị gán cứng (hardcoded) trong mã nguồn template `product.html`.
- Người quản trị (Admin) chỉ có thể sửa tên và đoạn mô tả cơ bản của sản phẩm, không thể linh hoạt thay đổi các tiêu chí thông số kỹ thuật (specs) khi có sự biến động về quy cách gia công, nguyên vật liệu hoặc dịch vụ kèm theo.

### 1.2. Mục tiêu giải pháp
- Cho phép người quản trị toàn quyền cấu hình **Nhãn Badge**, **Tên sản phẩm**, **Bảng thông số kỹ thuật động (Dynamic Specs Table)** và **Đoạn mô tả chi tiết sản phẩm** cho cả 3 dòng sản phẩm chủ lực:
  1. **Dây đeo thẻ in chuyển nhiệt cao cấp** (`lan-1`)
  2. **Thẻ nhựa PVC in theo yêu cầu** (`acc-1`)
  3. **Vỏ đựng thẻ (Card holder) in theo yêu cầu** (`acc-2`)
- Thiết kế giao diện Quản trị tiện lợi nhất: Tích hợp hệ thống **Tab chuyển nhanh trực quan 3 sản phẩm** ngay trong trang Quản lý sản phẩm (`/admin/products`), hỗ trợ thêm/xóa/sửa từng dòng thông số một cách mượt mà, không gián đoạn.

---

## 2. THIẾT KẾ DỮ LIỆU & KIẾN TRÚC HỆ THỐNG

### 2.1. Cấu trúc dữ liệu thông số kỹ thuật (Specs Data Schema)
Mỗi sản phẩm lưu trữ trường `specs_json` dạng JSON mảng các đối tượng:
```json
[
  {
    "icon": "ruler",
    "label": "Bản rộng",
    "value": "1.5 cm / 2.0 cm / 2.5 cm (1.5cm / 2.0cm / 2.5cm)"
  },
  {
    "icon": "layers",
    "label": "Chất liệu",
    "value": "Lụa Satin Cao Cấp"
  },
  {
    "icon": "check-circle-2",
    "label": "Tiêu chuẩn in",
    "value": "In chuyển nhiệt 2 mặt sắc nét, bền màu"
  },
  {
    "icon": "sparkles",
    "label": "Phụ kiện",
    "value": "Móc cua kim loại, khóa an toàn, khóa nối"
  },
  {
    "icon": "box",
    "label": "Nhận in từ",
    "value": "10 dây"
  },
  {
    "icon": "clock",
    "label": "Thời gian sản xuất",
    "value": "2-4 ngày làm việc"
  },
  {
    "icon": "pen-tool",
    "label": "Thiết kế demo",
    "value": "Hỗ trợ thiết kế cơ bản 2D"
  },
  {
    "icon": "truck",
    "label": "Giao hàng",
    "value": "Toàn quốc"
  },
  {
    "icon": "file-text",
    "label": "Hóa đơn",
    "value": "Có VAT"
  }
]
```

### 2.2. Trường Badge & Mô tả
- `badge`: Chuỗi ký tự nhãn phụ nổi bật trên đầu sản phẩm (ví dụ: `DÂY ĐEO THẺ IN THEO YÊU CẦU`).
- `description`: Đoạn văn bản giới thiệu sản phẩm chi tiết.

### 2.3. Cơ chế tương thích ngược (Backward Compatibility & Fallback)
- Nếu một sản phẩm chưa có dữ liệu `specs_json` tùy biến trong DB, template tự động fallback về danh sách thông số chuẩn hiện tại của danh mục đó (`lanyard`, `pvc`, `holder`), đảm bảo giao diện ngoài Storefront luôn hiển thị đầy đủ, không bao giờ bị lỗi hiển thị hay gãy trang.

---

## 3. THIẾT KẾ GIAO DIỆN QUẢN TRỊ (ADMIN UI)

### 3.1. Bố cục trang Quản lý sản phẩm (`/admin/products`)
- **Header**: Tiêu đề trang, nút quay lại, nút lưu nhanh.
- **Thanh Navigation 2 Tab**:
  - `[Danh sách sản phẩm]`: Bảng quản lý tổng thể như hiện tại.
  - `[Cấu hình thông số & Mô tả]`: Khu vực quản trị chi tiết 3 dòng sản phẩm.
- **Hệ thống 3 Sub-tab Sản phẩm**:
  - `[🏷️ Dây đeo thẻ]`
  - `[💳 Thẻ nhựa PVC]`
  - `[🪪 Vỏ đựng thẻ]`
- **Khu vực Form chỉnh sửa**:
  1. **Ô nhập Nhãn phụ (Badge)** (VD: `DÂY ĐEO THẺ IN THEO YÊU CẦU`).
  2. **Ô nhập Tên hiển thị sản phẩm** (VD: `Dây đeo thẻ in chuyển nhiệt cao cấp`).
  3. **Bảng Thông số kỹ thuật động (Specs Table)**:
     - Dòng tiêu đề: Biểu tượng | Tên tiêu chí (Nhãn) | Nội dung chi tiết (Giá trị) | Xóa
     - Mỗi dòng gồm 1 ô chọn Icon (Ruler, Layers, Check, Sparkles, Box, Clock, Pen-tool, Truck, File-text, Palette, Shield), 1 ô nhập Tên tiêu chí, 1 ô nhập Nội dung giá trị, và nút Xóa dòng `[✕]`.
     - Nút `[+ Thêm thông số mới]` nằm dưới chân bảng.
  4. **Ô nhập Thông tin sản phẩm (Đoạn mô tả chi tiết)**: Khung Textarea lớn, dễ thao tác.
  5. **Nút `[💾 Lưu thông tin sản phẩm]`**: Bấm lưu gửi dữ liệu AJAX hoặc Form POST an toàn kèm CSRF Token.

---

## 4. KẾ HOẠCH TRIỂN KHAI THEO QUY TẮC

1. **Bước 1**: Xuất ảnh UI Mockup trực quan `mockup_admin_product_specs.png` để người dùng phê duyệt thiết kế giao diện (Quy tắc 12).
2. **Bước 2**: Khởi tạo migration dữ liệu (bổ sung trường `badge`, `specs_json` cho bảng `products` nếu chưa có).
3. **Bước 3**: Cập nhật Backend Data Service & Admin Routes để tiếp nhận và lưu trữ `badge`, `specs_json`, `description`.
4. **Bước 4**: Cập nhật Admin Template (`frontend/admin/templates/products.html`) với hệ thống Tab và Bảng thông số động.
5. **Bước 5**: Cập nhật Storefront Template (`frontend/storefront/templates/product.html` và `templates/product.html`) render linh hoạt từ `specs_json`.
6. **Bước 6**: Chụp ảnh kiểm chứng thực tế trang Admin và trang Storefront xác nhận hoàn thành 100%.
