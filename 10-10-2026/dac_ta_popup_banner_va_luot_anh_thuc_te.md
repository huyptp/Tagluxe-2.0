# TÀI LIỆU ĐẶC TẢ KỸ THUẬT & NGHIỆP VỤ
## TRIỂN KHAI POPUP BANNER QUẢNG CÁO CHIẾN DỊCH & TỐI ƯU KHUNG ẢNH THỰC TẾ TRƯỢT THỦ CÔNG

---

- **Dự án**: Nền tảng Báo giá & Quản trị TAGLUXE
- **Ngày thực hiện**: 10-10-2026
- **Trạng thái**: Đã triển khai & Kiểm thử hoàn tất
- **Môi trường**: Worktree & Main Repository (`D:\Antigravity\TAGLUXE`)
- **Lưu ý triển khai**: Lưu cục bộ hoàn toàn, chỉ đẩy lên GitHub khi có lệnh xác nhận từ người dùng.

---

### 1. MỤC TIÊU VÀ BỐI CẢNH NÂNG CẤP

#### 1.1. Bối cảnh
1. **Dải ảnh thực tế trên trang chủ**: Trước đây, các dải ảnh mẫu thực tế đã sản xuất (Dây đeo, Thẻ nhựa PVC, Vỏ đựng thẻ) sử dụng hiệu ứng marquee tự động chạy liên tục 2 hàng ngược chiều. Thiết kế này vừa tạo cảm giác chóng mặt, vừa tiêu tốn tài nguyên GPU render liên tục, đồng thời nhân bản lặp lại ảnh tới 4 lần khiến trang web tải chậm.
2. **Nhu cầu chạy chiến dịch khuyến mại**: Khi quản trị viên triển khai các đợt flash sale, ưu đãi mùa khai giảng hoặc chiến dịch sự kiện, website cần có một banner popup hiển thị ở chính giữa trang để thông báo cho khách hàng, có nút tắt linh hoạt và không ép buộc thời gian xem.

#### 1.2. Mục tiêu đạt được
1. **Dải ảnh thực tế (Dây đeo thẻ & Thẻ PVC 2 hàng chạy tự động, Vỏ thẻ 1 hàng trượt thủ công)**:
   - Xóa bỏ hoàn toàn thanh tiêu đề có 2 dòng chữ cũ ở cả 3 danh mục.
   - **Dây đeo thẻ & Thẻ nhựa PVC**: Đều chạy tự động **2 hàng song song ngược chiều** mượt mà liên tục (`marquee-track-forward` & `marquee-track-reverse`), tự động tạm dừng khi rê chuột (`:hover`) để khách dễ dàng xem chi tiết hoặc bấm click.
   - **Vỏ đựng thẻ**: Giữ dạng **1 hàng duy nhất** trượt ngang thủ công (`gallery-scroll-row`), khách tự vuốt hoặc kéo chuột xem rất gọn gàng.
   - **Nút hành động trên thẻ**: Đồng bộ toàn bộ chữ nút hành động thành **"Xem chi tiết $\rightarrow$"** thay vì chữ "Xem" hay "Chi tiết" ngắn ngủn trước đây.
2. **Quản lý Banner Quảng Cáo Chiến Dịch trong Admin (`/admin/campaign-banner`)**:
   - Thêm nút và trang quản lý riêng biệt "Banner Chiến Dịch" trên thanh điều hướng Admin.
   - Quản trị viên có thể tải lên ảnh banner mới (hỗ trợ JPG, PNG, WEBP), bật/tắt nhanh bằng công tắc, hoặc bấm nút **Xóa Ảnh Banner**.
   - **Ràng buộc an toàn tuyệt đối (Strict Safeguard)**: Khi quản trị viên chưa tải ảnh lên hoặc khi bấm xóa ảnh banner đi, hệ thống tự động khóa và **TUYỆT ĐỐI KHÔNG HIỂN THỊ** popup banner trên website.

---

### 2. QUY CHUẨN TRẢI NGHIỆM NGƯỜI DÙNG (UI/UX)

#### 2.1. Trải nghiệm Popup Banner tại Storefront
- **Vị trí hiển thị**: Căn giữa màn hình trên nền tối mờ sang trọng (`rgba(0, 0, 0, 0.75)` kèm hiệu ứng `backdrop-filter: blur(4px)`).
- **Nút đóng [X]**: Nút tròn nổi bật ở góc trên bên phải, khách click nút [X] hoặc click ra ngoài vùng nền mờ để đóng ngay lập tức.
- **Không giới hạn thời gian**: Không có bộ đếm ngược ép tắt, khách hàng có thể đọc thông tin ưu đãi bao lâu tùy thích.
- **Ghi nhớ phiên (`sessionStorage`)**: Khách đóng một lần thì trong cùng phiên duyệt web sẽ không bị popup làm phiền lại; khi mở tab mới hoặc phiên mới thì popup sẽ xuất hiện lại.

#### 2.2. Trải nghiệm Dải ảnh thực tế
- **Dây đeo thẻ (Chạy tự động)**: 2 hàng ảnh tự động chạy ngược chiều nhau vô tận, tốc độ êm ái (45s - 48s), viền mờ 2 bên (`mask-image`), khi đưa chuột vào thì tạm dừng ngay để khách click xem chi tiết sản phẩm.
- **Thẻ nhựa PVC & Vỏ đựng thẻ (1 hàng trượt thủ công)**: Toàn bộ mẫu ảnh hiển thị trên 1 hàng duy nhất, thanh cuộn mỏng (6px) màu xám nhạt, hỗ trợ kéo chuột và vuốt cảm ứng mobile.
- **Nút "Xem chi tiết"**: Thiết kế nổi bật màu xanh dương thương hiệu, kèm biểu tượng mũi tên điều hướng, giúp khách hàng dễ dàng nhận biết và click vào trang chi tiết sản phẩm.

---

### 3. CÁC TỆP NGUỒN ĐÃ TRIỂN KHAI VÀ ĐỒNG BỘ

| STT | Tệp tin | Vai trò cập nhật |
|:---:|:---|:---|
| 1 | `backend/services/data_service.py` | Bổ sung hàm `get_campaign_banner_config()`, `save_campaign_banner_config()`, `delete_campaign_banner()` với logic bảo vệ nghiêm ngặt |
| 2 | `backend/admin/routes.py` | Thêm các route: `GET /admin/campaign-banner`, `POST /admin/campaign-banner/update`, `POST /admin/campaign-banner/delete`, `POST /admin/campaign-banner/toggle` |
| 3 | `backend/api/routes.py` | Thêm endpoint `GET /api/campaign-banner` trả về cấu hình banner JSON |
| 4 | `backend/__init__.py` | Tiêm biến `campaign_banner` vào Context Processor toàn cục cho Storefront |
| 5 | `frontend/admin/templates/campaign_banner.html` | Giao diện quản trị Banner Chiến Dịch hoàn chỉnh (Upload, Bật/Tắt, Xóa ảnh, Live Preview) |
| 6 | `frontend/admin/templates/base.html` | Thêm liên kết điều hướng "Banner Chiến Dịch" trên thanh menu Admin |
| 7 | `frontend/storefront/templates/base.html` | Thêm markup popup modal, CSS responsive và JavaScript điều khiển phiên hiển thị banner |
| 8 | `frontend/storefront/templates/index.html` | Xóa 2 dòng chữ tiêu đề, dừng auto-run, chuyển đổi ảnh thực tế: Dây đeo (2 hàng song song), Thẻ PVC & Vỏ thẻ (1 hàng duy nhất) trượt thủ công |
| 9 | `frontend/storefront/static/css/style.css` | Định nghĩa CSS cho `.lanyard-gallery-container`, `.gallery-scroll-box`, `.gallery-scroll-row` |
| 10 | `storage/campaign_banner.json` | Tệp lưu trữ cấu hình trạng thái và đường dẫn ảnh banner của chiến dịch |

---

### 4. HƯỚNG DẪN QUẢN TRỊ VIÊN VẬN HÀNH

1. Đăng nhập trang Admin và bấm vào mục **"Banner Chiến Dịch"** trên thanh menu (hoặc truy cập `http://localhost:5000/admin/campaign-banner`).
2. **Khi muốn chạy chiến dịch mới**:
   - Bấm vào khung tải ảnh để chọn ảnh banner từ máy tính cá nhân.
   - Tích chọn "Bật hiển thị popup ngay sau khi lưu" (hoặc gạt công tắc Bật).
   - Bấm **"Lưu Cấu Hình Banner"**.
   - Kiểm tra màn hình **Mô Phỏng Trực Quan (Live Preview)** bên phải để đảm bảo banner hiển thị đẹp mắt.
3. **Khi muốn kết thúc chiến dịch**:
   - Gạt công tắc sang **Tắt** để tạm ẩn popup; HOẶC
   - Bấm nút đỏ **"Xóa Ảnh Banner"** để gỡ hoàn toàn ảnh banner khỏi hệ thống $\rightarrow$ Popup sẽ lập tức biến mất hoàn toàn khỏi website.

---

### 5. KHẮC PHỤC LỖI KỸ THUẬT & KIỂM ĐỊNH THỰC TẾ (HOTFIX)

#### 5.1. Mô tả sự cố phát hiện
- **Hiện tượng**: Khi quản trị viên truy cập trang `/admin/campaign-banner` bị phản hồi mã lỗi `500 Internal Server Error`.
- **Nguyên nhân gốc rễ**: Tại file `backend/admin/routes.py`, dòng 952 gọi hàm không tồn tại: `csrf_token=get_or_create_csrf_token()`. Trong khi đó, hàm chuẩn của hệ thống là `get_csrf_token()` (định nghĩa tại dòng 65).

#### 5.2. Biện pháp xử lý
- Đã chỉnh sửa dòng 952 trong `backend/admin/routes.py`:
  ```python
  return render_template('admin/campaign_banner.html', banner=banner, csrf_token=get_csrf_token())
  ```
- Đồng bộ file đã sửa sang kho chính `D:\Antigravity\TAGLUXE\backend\admin\routes.py`.

#### 5.3. Kết quả kiểm thử tự động
- `GET /admin/campaign-banner` $\rightarrow$ Mã phản hồi **200 OK**, giao diện hiển thị đầy đủ thẻ quản trị, khung upload và khu vực mô phỏng.
- `POST /admin/campaign-banner/toggle` (khi chưa có ảnh) $\rightarrow$ Mã phản hồi **400 Bad Request**, chặn kích hoạt an toàn.
- `POST /admin/campaign-banner/delete` $\rightarrow$ Mã phản hồi **200 OK / 302 Redirect**, xóa ảnh và tắt hiển thị chính xác.

