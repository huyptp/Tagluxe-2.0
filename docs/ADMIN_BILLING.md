# In bill và QR thanh toán

Trong **Báo giá khách hàng → Mở hồ sơ → In bill / QR**, admin mở phiếu thanh toán riêng, chọn **In bill / Lưu PDF**. Bản mẫu dùng khổ A4; trên điện thoại các khối thông tin tự xếp dọc. Bill lấy thông tin khách, quy cách, phụ kiện, số lượng, giá và VAT từ báo giá đã lưu. Giá tổng là số tiền thực tế đã lưu, không tính lại theo bảng giá hiện tại.

Chủ shop cấu hình tại **Thanh toán & in bill**. Cấu hình lưu trong `site_settings` với khóa `payments`, dùng chung giữa các phiên và các máy chủ khi kết nối cùng PostgreSQL. Không cần biến Environment mới hay thay cấu trúc bảng. Tài khoản ngân hàng thật và QR gốc không được ghi trong mã nguồn.

Tư vấn và quản lý được xem/in bill; nhân viên nội dung không được xem. Chỉ chủ shop được thay cấu hình nhận tiền. Các trang bill và ảnh QR yêu cầu đăng nhập, không lưu cache. QR được tạo ngay trên máy chủ bằng thư viện `qrcode`, không gọi dịch vụ ảnh QR bên ngoài.

QR gốc của ngân hàng có thể dùng tài khoản định danh thay cho số tài khoản hiển thị. Khi cấu hình `source_qr`, hệ thống kiểm tra CRC, ngân hàng, loại chuyển khoản tài khoản VND và giữ các trường mở rộng của ngân hàng. Bill thêm số tiền cùng nội dung `TL...` theo mã báo giá; với mã quá dài, dùng SHA-256 rút gọn để nội dung không quá 25 ký tự. Khi đổi tài khoản, phải xóa/thay QR gốc để tránh giữ mã nhận tiền cũ.

Danh sách ngân hàng công khai tại `backend/services/payment_banks.json` được lấy từ API https://api.vietqr.io/v2/banks ngày 28/10/2026. Tài liệu: https://www.vietqr.io/api-bank. Danh sách cần được làm mới khi có ngân hàng thay đổi; thao tác này không gửi dữ liệu khách hoặc tài khoản nhận tiền lên API.

Không tạo QR nếu báo giá đã hủy, chưa cấu hình ngân hàng hoặc số tiền không hợp lệ. In/quét bill không tự đánh dấu đã thanh toán. Đây là phiếu đề nghị thanh toán, không phải hóa đơn thuế, không theo dõi tiền cọc và không đối soát giao dịch ngân hàng. Shop cần quét thử bằng ứng dụng ngân hàng để kiểm tra tên người nhận trước khi sử dụng với khách.

Kiểm thử dùng SQLite tách biệt dữ liệu thật: `tests.test_billing.BillingTest`. Có kiểm tra phân quyền, CSRF, lưu lại cài đặt, VAT, nội dung khách được escape, CRC, trường định tuyến ngân hàng và đọc lại QR. Bản xem thử/PDF và cấu hình thật chỉ nằm trong thư mục `backup/` đã bỏ qua bởi Git.
