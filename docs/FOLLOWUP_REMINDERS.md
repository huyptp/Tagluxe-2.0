# Email nhắc lịch liên hệ

Nhắc lịch lấy dữ liệu trực tiếp từ database của web, bao gồm `customer_profiles.follow_up_on` và `quote_admin_states.follow_up_on`. Không lấy lịch từ bản sao Google Sheets vì hồ sơ CRM nhập tay chưa đồng bộ sang bảng tính.

## Hành vi

- Mặc định chưa bật. Chủ shop mở **Email & nhắc lịch → Email nhắc liên hệ** hoặc nút **Nhắc lịch qua email** trong khu vực khách hàng.
- Chọn bật, email nhận và giờ bắt đầu. Email mặc định từ `ADMIN_NOTIFICATION_EMAIL` hiện có; giờ mặc định 09:00 Việt Nam.
- Lịch chạy Google Apps Script kiểm tra khoảng 15 phút một lần. Chỉ gửi từ giờ đã chọn, với ngày hẹn hôm nay hoặc quá hạn.
- Thư tổng hợp tối đa 50 lịch trong một lượt; bao gồm tên, số điện thoại, người phụ trách, ngày hẹn và link vào hồ sơ. Nhiều lịch tiếp theo được xử lý ở lượt sau; lịch mới thêm trong ngày không bị chặn bởi lịch đã gửi trước đó.
- Một lịch/ngày/email nhận có khóa duy nhất trong database. Sửa ghi chú không tạo thư nhắc lặp; đổi ngày hẹn tạo lịch nhắc mới. Quá hạn vẫn còn hiệu lực sẽ nhắc lại ngày hôm sau.
- Khách `Đã chốt`, `Chưa chốt`, `Tạm dừng` được loại khỏi nhắc chăm sóc hồ sơ, giống danh sách khách đến hẹn. Báo giá `Đã xong`/`Đã hủy` không được nhắc theo lịch báo giá. Bỏ lịch hoặc chuyển ngày tương lai cũng ngừng nhắc.
- Xóa khách/báo giá dọn các dấu gửi liên quan trong cùng giao dịch. Việc này không thể thu hồi thư đã được Google nhận hoặc một lượt gửi đang thực hiện.
- Danh sách người nhận báo giá mới không bị sửa. Nhắc lịch chỉ gửi tới một email do chủ shop chọn.

## Triển khai sau khi duyệt

1. Đẩy bản web mới lên GitHub để Render tự triển khai. Không thêm biến Environment. App tự tạo `follow_up_deliveries`, index và bật RLS khi chạy với Supabase.
2. Trong **admin web chính thức**, bật/lưu nhắc lịch. Mở **Kết nối với Google Sheets đang dùng** và sao chép thiết lập JSON. Khóa ngẫu nhiên chỉ chủ shop xem, lưu trong database; không đưa vào Git.
3. Thay toàn bộ mã trong dự án Apps Script đang dùng bằng `integrations/google_sheets/google_sheets_script.js`. Giữ nguyên các Script Properties trước đây, đặc biệt `WEBHOOK_SECRET`; không đổi URL webhook hiện tại.
4. Chạy `setupFollowUpReminders` trong Apps Script, hoặc tải lại bảng tính rồi dùng menu **TagLuxe Admin → Kết nối email nhắc lịch**. Dán JSON đã sao chép và xác nhận quyền Google nếu được hỏi.
5. Hàm cài đặt tạo đúng một trigger `pollFollowUpReminders`, kiểm tra mỗi 15 phút. Chạy lại không nhân đôi trigger; chỉ dọn trigger trùng thuộc tính năng này. Không thay các trigger khác.
6. Có thể chạy `pollFollowUpReminders` để kiểm tra ngay; việc này gửi email thật nếu đã tới giờ và có lịch cần nhắc. Trang admin sẽ hiển thị lần kiểm tra gần nhất và lịch sử trạng thái. Không cần mở admin để lịch chạy hoạt động.

Trigger đọc mã dự án đang lưu; thay đổi này không dùng action mới của webhook nhận báo giá. Không cần thay URL triển khai webhook hoặc cấu hình trên Render để cài nhắc lịch.

## Bảo vệ và độ tin cậy

RPC chỉ nhận POST với khóa riêng trong Authorization; không chấp nhận khóa trong URL, không dùng phiên đăng nhập thay khóa. Chuẩn hóa người nhận từ cấu hình server; caller không chọn được email nhận hay nội dung thư. Phản hồi private/no-store. Dữ liệu gửi Google chỉ phục vụ thư nhắc; không tạo bản ghi khách/báo giá giả trong bảng tính.

Database giữ dấu nhận việc, hạn giữ 10 phút, trạng thái, số lần thử và thời gian gửi UTC. Màn hình chuyển thời gian sang Việt Nam. Claim dùng khóa duy nhất và cập nhật có điều kiện; ACK cũng kiểm tra token hiện tại. Lịch sử và chống trùng tồn tại qua đăng nhập/khởi động lại.

Apps Script dùng Script Lock, chỉ ACK sau MailApp chấp nhận thư và lưu batch chờ ACK trong Script Properties. Nếu xác nhận bị lỗi, lượt sau ACK lại trước khi chuẩn bị thư mới. Lỗi gửi thử lại sau một giờ; lỗi MailApp lặp 5 lần cần kiểm tra, lịch ngày tiếp theo có thể được thử mới. Hết hạn mức Google vẫn giữ trạng thái thử lại để gửi được khi hạn mức hồi phục.

MailApp không cung cấp idempotency key: vẫn có cửa sổ gián đoạn hiếm giữa Google chấp nhận thư và lưu dấu chờ ACK. Đây là chống gửi lặp thông thường, không bảo đảm exactly-once tuyệt đối hoặc thư chắc chắn vào Inbox. Trigger/cold start/hạn mức có thể làm chậm hơn 15 phút; 09:00 là giờ bắt đầu, không phải cam kết gửi đúng phút.

Kiểm thử Python: `tests/test_followup_reminders.py`. Kiểm thử Apps Script VM: `tests/test_followup_clock.js`; kiểm tra trigger không trùng, ACK retry, quota, lỗi MailApp, payload và URL. Tất cả dùng dữ liệu riêng, không gửi email thật. Các bài Sheets bridge/CRM cũ cũng được chạy để kiểm tra bảo toàn đồng bộ.
