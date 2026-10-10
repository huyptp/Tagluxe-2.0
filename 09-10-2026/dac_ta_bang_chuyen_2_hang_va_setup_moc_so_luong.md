# ĐẶC TẢ KỸ THUẬT: BĂNG CHUYỀN ẢNH 2 HÀNG VÀ BẢNG SETUP MỐC SỐ LƯỢNG ADMIN

**Dự án**: TagLuxe E-Commerce & B2B  
**Ngày thực hiện**: 09-10-2026  
**Trạng thái**: Đã phê duyệt (Approved)  

---

## 1. TỔNG QUAN YÊU CẦU

### 1.1. Băng Chuyền Ảnh 2 Hàng Storefront (Double-Row Marquee Runner)
- **Vấn đề**: Trước đây các mục Dây đeo, Thẻ nhựa PVC, Vỏ đựng thẻ chỉ hiển thị 1 hàng ảnh chạy ngang. Trên màn hình máy tính desktop/laptop, phần hiển thị có cảm giác trống trải, chưa khoe được trọn vẹn số lượng mẫu mã đa dạng phong phú.
- **Giải pháp**:
  - Nâng cấp thành **2 hàng ảnh chạy song song đối xứng** cho cả 3 danh mục:
    1. Dây đeo thẻ in chuyển nhiệt (`#products`)
    2. Thẻ nhựa PVC cao cấp (`#the-nhua-pvc`)
    3. Vỏ đựng thẻ (`#vo-dung-the`)
  - **Chuyển động ngược chiều (Reverse Scroll)**: Hàng 1 chạy từ phải qua trái, Hàng 2 chạy từ trái qua phải, tạo chiều sâu thị giác hiện đại (Modern Luxury Gallery Wall).
  - **Hover to pause**: Rê chuột vào hàng nào thì hàng đó dừng lại để khách hàng quan sát kỹ hoặc bấm xem mẫu chi tiết.
  - **Fit-To-Screen**: Tinh chỉnh kích thước card ảnh (`width: 180px`, `img height: 140px`) để toàn bộ section vừa khít 1 màn hình máy tính chuẩn (1080p), không bị tràn hay phải cuộn.

### 1.2. Bảng Setup Mốc Số Lượng & Giá Trong Trang Admin (`/admin/accessories`)
- **Vấn đề**: Bảng biểu giá trước đây chỉ cho phép chỉnh sửa giá tiền `unit_price`, còn cột mốc số lượng là chữ tĩnh cố định (như `10 - 21 dây`). Khi chính sách bán sỉ thay đổi hoặc muốn thêm/bớt khoảng số lượng, admin không thể can thiệp.
- **Giải pháp**:
  - Biến cột mốc số lượng thành **2 ô nhập linh hoạt `[min_qty]` – `[max_qty]`** trên từng dòng.
  - Thêm nút **Xóa mốc `✕`** cho từng dòng biểu giá.
  - Thêm nút **`➕ Thêm Mốc Mới`** dưới chân mỗi bảng để chủ động sinh dòng mới.
  - Nút **`💾 Lưu Toàn Bộ Mốc & Giá Mới`** gửi toàn bộ danh sách mốc (bao gồm mốc sửa, mốc mới, mốc xóa) lên backend cập nhật CSDL `PriceTier`.

---

## 2. THIẾT KẾ KIẾN TRÚC & DỮ LIỆU

### 2.1. Storefront Front-end
- Template: `frontend/storefront/templates/index.html` và `templates/index.html`.
- CSS: `frontend/storefront/static/css/style.css` và `static/css/style.css`.
- Logic chia ảnh:
  - Dây đeo: 25 ảnh chia thành hàng 1 (13 ảnh) và hàng 2 (12 ảnh).
  - Thẻ PVC: 6 ảnh chia thành hàng 1 (3 ảnh đầu lặp) và hàng 2 (3 ảnh sau lặp).
  - Vỏ thẻ: 6 ảnh chia thành hàng 1 (3 ảnh đầu lặp) và hàng 2 (3 ảnh sau lặp).

### 2.2. Backend Data Service & Admin API
- Service: `backend/services/data_service.py`
  - Hàm `save_price_tier_matrix(tiers_data)`:
    - Xử lý thêm mới, cập nhật mốc `min_qty`, `max_qty`, `unit_price`, hoặc xóa bỏ `PriceTier`.
    - Đồng bộ tự động 2 chiều giữa `pvc_5.4x8.6` và `pvc`.
- Route: `backend/admin/routes.py`
  - Route `POST /admin/pricing/update`: tiếp nhận JSON array toàn bộ các mốc và lưu vào DB an toàn qua transaction.
