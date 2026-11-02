# Lưu thay đổi admin qua các phiên đăng nhập

Kiểm tra ngày 29/10/2026. Thông tin nghiệp vụ được lưu trong database; cookie đăng nhập chỉ xác thực người dùng. Các request admin đọc lại database và trả `Cache-Control: private, no-store`.

## Nơi lưu

| Dữ liệu | Nơi lưu |
| --- | --- |
| Sản phẩm, thông số, hiển thị và danh sách ảnh | `products` |
| Giá theo số lượng và mốc số lượng | `price_tiers` |
| Phụ kiện, giá, mô tả và đường dẫn ảnh | `accessories` |
| Báo giá và trạng thái | `quotes` |
| Hồ sơ liên hệ, địa chỉ, nhu cầu, ngày cần hàng, lịch hẹn | `customer_profiles` |
| Ghi chú và chăm sóc từng báo giá | `quote_admin_states` |
| Ảnh demo, banner, người nhận email, cấu hình QR | `site_settings` |
| Tài khoản nhân viên và phân quyền | `admin_users` |
| Nội dung file ảnh tải lên | Supabase Storage; đường dẫn liên kết lưu trong database |

Sau khi bấm Lưu và nhận thông báo thành công, người dùng khác hoặc phiên mới đọc được dữ liệu đã lưu khi mở/tải lại trang. Một trang đang mở sẵn không tự cập nhật trực tiếp theo thời gian thực. Hồ sơ khách và chăm sóc báo giá có kiểm tra phiên bản để từ chối ghi đè từ biểu mẫu cũ.

Google Sheets là luồng báo giá riêng; hồ sơ CRM nhập tay và ghi chú nội bộ chưa được sao chép sang Sheets. Điều này không ảnh hưởng đến lưu giữ trong Supabase qua đăng nhập.

## Xác minh

- Kết nối dự án hiện tại: PostgreSQL, kho ảnh Supabase; đủ các bảng theo model. Đây là kiểm tra trực tiếp database và kho ảnh, không phải kiểm tra hoặc thay đổi Environment trên Render.
- Kiểm tra chỉ đọc: 52/52 ảnh đang được dữ liệu cửa hàng tham chiếu trong kho Supabase trả HTTP 200; 6 ảnh đóng gói trong mã nguồn có trên đĩa.
- Kiểm thử biệt lập: ghi bằng các route admin, đọc từ phiên B đã đăng nhập trước đó, đăng xuất/đăng nhập lại, đóng kết nối và tạo ứng dụng mới trên cùng database. Kiểm tra sản phẩm, thay ảnh, giá/mốc số lượng, phụ kiện, hồ sơ khách, trạng thái, chăm sóc báo giá, ảnh demo, banner, người nhận email, thanh toán và nhân viên.
- Kiểm tra lỗi: upload thất bại không thay ảnh sản phẩm đã lưu; commit cấu hình thất bại phải rollback, giữ giá trị đã lưu và cho phép thử lại.
- Tổng bộ kiểm thử liên quan sau cập nhật lưu tại chỗ: 75 kiểm thử đạt (kiểm tra lại ngày 02/11/2026). Database kiểm thử là file tạm riêng; upload mạng được mô phỏng; không tạo khách thử, gửi email hoặc sửa dữ liệu thật.
- Sửa kèm: cho phép lưu mô tả/tiêu đề phụ kiện rỗng có chủ ý; rollback giao dịch cấu hình khi lưu thất bại.

Bài kiểm thử bổ sung: `tests/test_admin_session_persistence.py` (thư mục tests được quy định giữ local trong `.gitignore`). Bản kiểm tra chỉ đọc và kết quả chi tiết nằm trong `backup/persistence-audit-20261029/`, cũng được loại khỏi Git.

## Lưu tại chỗ trong admin

Các biểu mẫu lưu khách, chăm sóc báo giá, sản phẩm/thông số, bảng giá, phụ kiện, ảnh demo, banner, tài khoản nhận tiền, nhân viên và người nhận email gửi POST có CSRF và nhận phản hồi JSON. Backend chỉ báo thành công sau thao tác lưu database đã thành công. Các luồng đăng nhập/đăng xuất và xóa hồ sơ giữ hành vi riêng.

Cập nhật trạng thái báo giá riêng lẻ/hàng loạt cũng phản hồi tại chỗ, cập nhật nhãn trạng thái mà không chuyển khỏi danh sách hoặc trang chi tiết.

Không chuyển trang hoặc tải lại cả trang khi lưu thành công. Biểu mẫu giữ nguyên, nút hiển thị Đang lưu và khóa chống gửi lặp trong lúc chờ. Nếu lỗi xác thực, kiểm tra dữ liệu, xung đột phiên bản hoặc kết nối, nội dung nhập vẫn còn để xử lý. Hồ sơ khách/chăm sóc báo giá nhận phiên bản mới sau mỗi lần lưu; hồ sơ/sản phẩm mới chuyển action sang route chỉnh sửa để lưu tiếp không tạo bản ghi trùng.

Bảng giá/phụ kiện chỉ làm mới phần dữ liệu liên quan; giữ nhóm đang chọn, bộ lọc và vị trí cuộn. Bảng giá dùng ID mới từ server sau khi thêm bậc. Nếu database đã lưu nhưng tải lại phần bảng thất bại, phải tải lại trang trước khi chỉnh tiếp để tránh tạo trùng. Đổi ảnh phụ kiện không còn gọi tải lại trang.

Đã kiểm tra bằng trình duyệt trên database mẫu local riêng: lưu hồ sơ khách hai lần liên tiếp, lưu bảng giá nhiều lần và hoàn tác sau lưu, sửa phụ kiện trong hộp thoại mà không đóng hộp/chuyển trang. Bài kiểm thử hợp đồng phản hồi: `tests/test_admin_inplace_save.py`. Bản thử và ảnh minh chứng nằm trong `backup/inplace-save-20261029/` và không đưa lên Git.
