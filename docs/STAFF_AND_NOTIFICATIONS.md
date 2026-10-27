# Nhân viên và email nhận báo giá

## Dùng trong admin

Chủ shop mở **Nhân viên & phân quyền** để tạo tài khoản bằng tên đăng nhập riêng,
họ tên, mật khẩu ban đầu từ 12 ký tự, email và nhóm quyền. Không tạo tài khoản
mẫu hoặc gửi thông tin đăng nhập tự động. Chủ shop chuyển thông tin cho đúng
nhân viên; nhân viên có mục **Tài khoản cá nhân** để đổi mật khẩu.

| Nhóm quyền | Được thao tác |
| --- | --- |
| Chủ shop hiện tại | Toàn bộ admin, tài khoản, người nhận email, nhật ký, xuất và xóa dữ liệu |
| Tư vấn khách hàng | Tổng quan, báo giá, khách hàng, trạng thái, lịch hẹn và ghi chú |
| Nội dung & hình ảnh | Sản phẩm, ảnh demo và banner; không xem khách hàng hoặc bảng giá |
| Quản lý vận hành | Báo giá, khách hàng, sản phẩm, bảng giá/phụ kiện và nội dung |

Nhân viên không được cấp quyền chủ shop, quản lý tài khoản/người nhận mail,
xuất CSV hoặc xóa toàn bộ hồ sơ báo giá/sản phẩm/phụ kiện. Mọi kiểm tra quyền
chạy ở máy chủ cho cả GET và POST; không chỉ ẩn menu. Các thao tác sửa nội dung
như bỏ ảnh hoặc sửa bậc giá nằm trong quyền nghiệp vụ tương ứng.

Khóa tài khoản chặn đăng nhập ngay, kết thúc phiên đang mở khi yêu cầu kế tiếp
đến máy chủ, đồng thời ngừng gửi thông báo theo tài khoản đó. Nếu cùng địa chỉ còn được thêm
riêng trong danh sách người nhận, chủ shop cần tắt cả mục đó. Đổi quyền, đặt lại mật khẩu hay
cập nhật tài khoản thay dấu xác thực của người đó. Tự đổi mật khẩu giữ phiên
hiện tại và kết thúc những phiên cũ khác. Nhật ký lưu đúng tên đăng nhập của
người thao tác, không lưu mật khẩu.

## Người nhận email

- Mở **Email thông báo** để thêm người nhận không cần quyền đăng nhập.
- Hoặc bật **Nhận email khi có báo giá mới** trong tài khoản nhân viên đang hoạt động.
- Tối đa 20 địa chỉ đang nhận, tự bỏ trùng, không cho nhập danh sách nhiều địa chỉ
  hoặc header email vào một ô. Mỗi người nhận thư riêng, không lộ địa chỉ đồng nghiệp.
- Danh sách rỗng được giữ là rỗng; không âm thầm quay về email mặc định.
- Trước khi có cấu hình riêng, email mặc định lấy từ `ADMIN_NOTIFICATION_EMAIL`.
- Bấm lưu không gửi thử, không gửi lại các báo giá cũ.

Danh sách và tài khoản lưu cùng PostgreSQL trong Supabase: bảng `admin_users`
và khóa `notifications` của bảng `site_settings`. Mật khẩu chỉ lưu hash scrypt.
Phiên đăng nhập của cả chủ shop và nhân viên phải có dấu xác thực bí mật khớp
trong database; dữ liệu vai trò từ cookie không tự cấp quyền. Phiên chủ shop cũ
trước bản nâng cấp cần đăng nhập lại một lần. Tài khoản chủ shop từ Environment
vẫn giữ nguyên, không tự tạo mật khẩu mới.

## Thứ tự triển khai

1. Sao lưu script hiện tại. Cập nhật toàn bộ `integrations/google_sheets/google_sheets_script.js`
   vào đúng dự án Apps Script đang dùng. Giữ thuộc tính `WEBHOOK_SECRET` khớp
   `GOOGLE_SHEET_SECRET` trên hosting. Dự án đang dùng đã có thuộc tính này.
2. Cập nhật **bản triển khai hiện có** bằng một phiên bản mới để giữ nguyên URL.
   `doGet` phải trả `notification_protocol: tagluxe-email-v2`. Không cần cấp lại
   quyền Gmail nếu quyền `script.send_mail` đã được cấp và chưa bị thu hồi.
3. Sau khi chủ shop duyệt, đẩy code website lên GitHub cho Render tự triển khai.
   Code tự tạo thêm bảng `admin_users` và bật RLS; không cần xóa hoặc nhập lại dữ liệu.
4. Đăng nhập lại admin, tạo nhân viên hoặc thay danh sách người nhận theo nhu cầu.

Khi có danh sách tùy chỉnh, web kiểm tra năng lực Apps Script trước khi gửi dữ
liệu. Nếu script còn cũ, tác vụ báo lỗi để chủ shop cập nhật; không gửi sang
script cũ có thể bỏ qua địa chỉ mới hoặc cố gửi về địa chỉ đã bị tắt. Google
vẫn áp dụng quyền/hạn mức gửi; danh sách người nhận không đảm bảo thư vào Inbox.

Script theo dõi các email còn chờ của từng báo giá. Nếu gửi được một phần, lần
thử lại bỏ qua các địa chỉ đã gửi thành công và loại người đã bị ngừng nhận.
Người mới được thêm không tự nhận báo giá cũ đang thử lại. Đây không phải bảo
đảm exactly-once tuyệt đối: MailApp không có idempotency key, việc lưu dấu sau
khi Google chấp nhận thư vẫn có thể lỗi trong tình huống gián đoạn hiếm gặp.

## Dashboard bảng tính

Bảng đang dùng được sửa tại chỗ, giữ các cột A–AC và công thức quản lý khách.
Dashboard có chọn kỳ, 8 chỉ số, 2 biểu đồ, trạng thái, việc cần xử lý và 10 báo
giá gần đây. Dữ liệu lấy từ bảng tính; thay trạng thái trực tiếp trong bảng tính
không đồng nghĩa đã cập nhật ngược trạng thái trên website. Các bảng có thể có
số lượng khác nhau khi hồ sơ bị xóa/khôi phục riêng; không tự xóa lịch sử.

Mục “Tiền đã thu trong kỳ” cộng cột Z của các báo giá được tạo trong kỳ chọn,
không phải dòng tiền thu theo ngày thanh toán, vì chưa có cột ngày thanh toán.
Script có kiểm tra giữ nguyên dashboard mới khi chạy menu khởi tạo cũ.

## Kiểm thử

Kiểm thử nhân viên, quyền theo route, CSRF, phiên bị thu hồi, email trùng/rỗng,
kiểm tra giao thức và nội dung payload dùng database riêng, không gửi mail thật.
Các tình huống Apps Script được chạy bằng Node với dịch vụ Google giả lập.
Không chạy `tests/test_security.py` bản cũ với database của shop.
