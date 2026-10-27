# Xóa khách hàng không chốt trong admin

Chủ shop mở **Khách hàng → Xem hồ sơ → Xóa khách hàng**. Trước khi xóa, trang
hiển thị tổng số báo giá cùng số điện thoại, yêu cầu nhập lại số điện thoại và
đánh dấu xác nhận. Nếu có báo giá đã chốt/đã xong, cần xác nhận bổ sung.

Khách hàng hiện được tổng hợp từ báo giá theo số điện thoại. Xóa khách sẽ xóa
toàn bộ báo giá cùng số đó khỏi database web, ghi chú/lịch hẹn riêng, tác vụ
đồng bộ đang chờ và kết quả chống gửi trùng tương ứng. Giữ nguyên khách khác
và nhật ký hoạt động. Chủ shop có thể chọn trạng thái **Đã hủy** thay cho xóa
nếu muốn giữ lịch sử tư vấn.

Thao tác là một transaction. Nếu database lỗi, toàn bộ thay đổi được rollback.
Nếu tác vụ đồng bộ đang có lease hoạt động, chưa cho xóa để tránh gửi một thông
báo đang xử lý. Nếu tập báo giá thay đổi sau khi mở trang xác nhận, yêu cầu xem
lại hồ sơ; không tự xóa thêm báo giá mới chưa được chủ shop xem.

Bản sao trên Google Sheets và email đã gửi không bị xóa. Bảng `quote_deletions`
chỉ giữ mã báo giá, người xóa và thời điểm để chức năng restore không nạp lại
báo giá đã chủ động xóa. Bảng có RLS như các bảng riêng khác. Nếu khách gửi một
yêu cầu mới với cùng số điện thoại, web vẫn tiếp nhận bình thường.

Quyền xóa kiểm tra trên máy chủ; tất cả tài khoản nhân viên bị chặn, kể cả khi
gửi POST trực tiếp. GET không xóa dữ liệu. Cần CSRF hợp lệ và xác nhận rõ ràng.
Kiểm thử dùng database riêng; không xóa hồ sơ khách thật khi phát triển.
