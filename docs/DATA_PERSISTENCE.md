# Lấy lại báo giá từ Google Sheets

Shop đang dùng Google Sheets để nhận báo giá. Code cũ gửi báo giá sang bảng tính,
nhưng trang admin chỉ đọc SQLite/PostgreSQL của web, chưa đọc ngược từ Sheets.
Nếu SQLite trên Render bị thay mới khi restart/deploy, cả báo giá và khách hàng
trên admin đều trống, dù các dòng đã đồng bộ vẫn còn trong Sheets. Đăng nhập không
có lệnh xóa báo giá. Chưa kiểm tra cấu hình Render thực tế.

## Bản sửa

- Giữ kết nối bảng tính hiện có, không bắt đổi sang PostgreSQL.
- Sau đăng nhập, nếu database chưa có báo giá và đã cấu hình Sheets, thử lấy lại
  các dòng từ tab `📋 QUẢN LÝ BÁO GIÁ`.
- Nút **Lấy lại báo giá & khách hàng** tại Admin → Tình trạng hệ thống để lấy thủ công.
- Chỉ thêm mã chưa có, không ghi đè trạng thái/ghi chú của hồ sơ đang có.
  Khách hàng tự hiện lại từ báo giá. Dòng sai/thiếu bị bỏ qua và có thống kê.
- Kiểm tra khả năng đọc qua GET trước khi POST, tránh script cũ hiểu nhầm lệnh đọc
  thành báo giá mới. GET chỉ trả phiên bản giao thức, không trả dữ liệu khách.
- POST đọc/ghi đều yêu cầu khóa xác thực. Nút admin yêu cầu đăng nhập và CSRF.
- Lỗi kết nối không xóa dữ liệu hiện có; lỗi phân trang hủy toàn bộ lần nhập đó.

## Cần thực hiện sau khi duyệt code

1. Cập nhật `integrations/google_sheets/google_sheets_script.js` vào Apps Script của
   **bảng tính đang dùng**, cập nhật deployment Web App hiện có. Không chạy
   `setupFullSystem` để khôi phục; đó là công cụ dựng giao diện.
2. Đặt `WEBHOOK_SECRET` trong Script Properties khớp với `GOOGLE_SHEET_SECRET`
   của web. Không ghi khóa thật vào code, GitHub hoặc tài liệu.
3. Giữ nguyên `GOOGLE_SHEET_WEBHOOK_URL` nếu cập nhật deployment hiện có.
4. Duyệt và đẩy code web lên GitHub. Render tự deploy như hiện tại.
5. Đăng nhập khi danh sách trống hoặc bấm nút lấy lại trong Hệ thống, đối chiếu
   báo giá và khách hàng với bảng tính.

Đẩy GitHub không tự cập nhật Apps Script. Chưa cập nhật script thì web vẫn chạy,
chức năng lấy lại sẽ báo cần cập nhật. Tắt việc lấy lại lúc đăng nhập bằng
`GOOGLE_SHEET_RESTORE_ON_LOGIN=false`; nút thủ công vẫn dùng được.

## Phạm vi dữ liệu

Chỉ báo giá **đã đồng bộ thành công** lên Sheets mới lấy lại được. Yêu cầu chưa đồng
bộ, ghi chú nội bộ, lịch hẹn, người phụ trách, audit log, ảnh upload và bảng giá tùy
chỉnh chưa có trong tab báo giá nên không phục hồi bằng cách này. Hàng đợi đồng bộ
vẫn chạy bất đồng bộ; đây chưa phải thay toàn bộ database bằng Sheets và chưa bảo
đảm giữ được yêu cầu chưa gửi sang Sheets trước khi host reset.

Dòng cũ chỉ có tổng tiền. Không tự suy diễn đơn giá/VAT: đơn giá chưa biết sẽ là 0.
Sau cập nhật, script thêm cột N lưu metadata đơn giá/VAT/đục lỗ cho báo giá mới hoặc
gửi lại. Giữ nguyên cột A–M và trạng thái dòng đã có.

Khi admin trống, lấy lại đưa về các báo giá còn trong Sheets, kể cả hồ sơ từng xóa
riêng trên web. Xóa trên web hiện không xóa bảng tính. Cần thống nhất cách xóa ở
nguồn nếu không muốn các dòng đó xuất hiện lại sau khôi phục.

Lần sửa này chỉ thay code local. Không sửa Render, đọc dữ liệu khách từ dịch vụ
thật hay cập nhật Apps Script thật. Kiểm thử dùng database tách biệt và dữ liệu giả.

Tham khảo về file tạm: https://render.com/docs/free.
