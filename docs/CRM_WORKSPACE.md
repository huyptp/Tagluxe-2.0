# Khách hàng & báo giá

Ngày cập nhật: 03/11/2026.

Menu quản trị chỉ còn một mục **Khách hàng & báo giá**, tại `/admin/crm`. Không thay đổi bảng hoặc chuyển đổi dữ liệu. Khách nhập tay và khách gửi báo giá website vẫn ghép theo số điện thoại.

## Luồng sử dụng

1. Mặc định xem theo khách hàng: tìm theo tên, số điện thoại, công ty hoặc mã báo giá; lọc nguồn, tình trạng và lịch chăm sóc.
2. Bấm tên khách hoặc **Xem báo giá** để mở nhanh ngay dưới dòng khách. Hiển thị tối đa 3 báo giá mới nhất, có ngày tạo, yêu cầu, giá trị, trạng thái và các nút thao tác.
3. Đổi trạng thái rồi bấm **Lưu** tại chỗ; **Chi tiết / chăm sóc** mở ghi chú và lịch theo báo giá; **In bill / QR** mở bản in ở tab khác.
4. **Sửa thông tin khách** và **Hồ sơ đầy đủ** nằm trong cùng khung mở nhanh. Khách chưa có báo giá vẫn được lưu và đặt lịch chăm sóc; không tạo báo giá hoặc doanh thu giả.
5. Khách có nhiều báo giá dùng **Xem đủ ... báo giá** để mở chế độ báo giá với bộ lọc chính xác theo số điện thoại. Các lối tắt trạng thái và lịch hẹn giữ bộ lọc khách; có nút **Bỏ lọc khách**.
6. Chế độ **Tất cả báo giá** nằm ngay trong khu vực này, dùng cho yêu cầu mới, lọc nâng cao, xuất CSV và cập nhật hàng loạt.

Các liên kết từ tổng quan, thanh tìm nhanh, hồ sơ khách và hồ sơ báo giá cùng trỏ về khu vực chung. Những địa chỉ cũ `/admin/customers` và `/admin/quotes` vẫn hiển thị đúng chế độ để giữ tương thích liên kết đã lưu. Các route POST, CSRF, lưu tại chỗ, phân quyền, in bill và xóa hồ sơ được giữ nguyên.

## Kiểm tra

- Quyền truy cập CRM tương đương quyền xem khách/báo giá: chủ shop, tư vấn và quản lý; nhân viên nội dung không được đọc dữ liệu khách.
- Truy vấn xem nhanh chỉ lấy 3 báo giá mới nhất cho mỗi khách trong trang hiện tại, dùng window function và tải thông tin chăm sóc theo lô. Không tải toàn bộ lịch sử cho từng dòng.
- Tìm kiếm báo giá nhận tên hồ sơ/công ty hiện tại và số điện thoại đã chuẩn hóa; tìm khách nhận cả mã báo giá. Đầu vào được escape khi tìm chuỗi, nội dung được escape khi hiển thị.
- Có kiểm thử riêng `tests/test_crm_workspace.py`, dùng database biệt lập: điều hướng, lịch sử đúng khách, giới hạn 3, khách chưa có báo giá, tìm kiếm chung, phân trang, phân quyền, escape và lưu tại chỗ.
- Bản xem thử và ảnh kiểm tra desktop/mobile nằm trong `backup/crm-workspace-20261103/`, không đưa lên Git. Dữ liệu kiểm thử không được đưa vào cơ sở dữ liệu thật.
