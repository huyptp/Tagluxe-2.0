# Hồ sơ khách từ Zalo và website

## Sử dụng

- Chọn **Thêm khách** trên thanh đầu trang hoặc **Khách hàng → Thêm khách hàng**. Bắt buộc tên và số di động Việt Nam; các mục khác có thể bổ sung sau.
- Nguồn: Zalo, Website, Facebook, Điện thoại, Trực tiếp, Giới thiệu, Khác. Lưu công ty, email, địa chỉ, nhu cầu, ghi chú nội bộ, người phụ trách, ngày cần hàng và ngày hẹn.
- Số điện thoại chuẩn hóa từ `+84`/`84` và bỏ khoảng trắng/dấu phân cách. Mỗi số có một hồ sơ. Nếu trùng hồ sơ đã nhập, màn hình giữ nội dung và đưa liên kết mở hồ sơ có sẵn.
- Hồ sơ nhập tay và báo giá website được ghép theo số điện thoại. Khách từ Zalo chưa có báo giá vẫn hiển thị với 0 báo giá. Hệ thống không tạo báo giá hoặc giá trị bán hàng giả để lưu khách.
- Tìm theo tên hồ sơ, tên từng dùng trong báo giá, số điện thoại hoặc công ty. Có lọc nguồn, tình trạng chăm sóc, khách đến hẹn và khách chưa có báo giá. Phân trang giữ bộ lọc.
- Tình trạng chăm sóc khách là thông tin riêng, không sửa trạng thái báo giá. Với khách web chưa bổ sung hồ sơ, trạng thái trên danh sách suy ra từ các báo giá. Khi có hồ sơ, tình trạng do người tư vấn quản lý.
- Hẹn hôm nay/quá hạn xuất hiện trong mục Đến hẹn liên hệ và lối tắt trên dashboard. Khách Đã chốt / Chưa chốt / Tạm dừng không được nhắc ở danh sách này. Lịch hẹn theo báo giá vẫn quản lý riêng.

## Lưu trữ và quyền

`CustomerProfile` lưu ở bảng `customer_profiles` trong database đang cấu hình. Với PostgreSQL/Supabase, hồ sơ tồn tại qua đăng nhập và lần triển khai. `init_db` tạo bảng mới theo model và bật RLS; file SQL thiết lập mới cũng được cập nhật. Không cần biến Environment mới, không xóa hoặc sửa các báo giá hiện hữu để nâng cấp.

Hồ sơ/ghi chú nhập tay chỉ nằm trong CRM, chưa đồng bộ thêm sang Google Sheets hoặc email. API báo giá công khai và bill không xuất các trường nội bộ này.

Chủ shop, nhân viên tư vấn và quản lý có quyền nhập/chỉnh khách; nhân viên nội dung không được xem. Chỉ chủ shop được xóa. Xóa khách bao gồm hồ sơ mới cùng các báo giá liên quan và dùng xác nhận theo số điện thoại/snapshot hiện tại. Nếu hồ sơ vừa đổi hoặc có báo giá mới, phải xem lại trước khi xóa. Hồ sơ nhập tay không có báo giá vẫn xóa được. Xóa một báo giá riêng không xóa hồ sơ liên hệ đã bổ sung.

Sửa hồ sơ dùng version để từ chối ghi đè từ màn hình cũ. Số điện thoại không đổi trực tiếp trên hồ sơ vì là khóa ghép lịch sử. Người dùng có thể tạo hồ sơ mới cho số khác; chưa có luồng gộp hai số điện thoại khác nhau.

## Giao diện

Thanh đầu trang có tìm khách nhanh và thêm khách; menu chia nhóm; dashboard có lối tắt công việc. Danh sách trên điện thoại chuyển thành thẻ. Biểu mẫu chia thông tin liên hệ, nhu cầu, kế hoạch chăm sóc, có nút lưu bám cuối màn hình và cảnh báo rời trang khi chưa lưu.

Kiểm thử nằm trong `tests/test_customer_profiles.py`, dùng cơ sở dữ liệu độc lập. Bản xem thử và khách mẫu ở `backup/customer-workspace-20261029/`; không đưa lên GitHub và không tạo khách thử trong Supabase.
