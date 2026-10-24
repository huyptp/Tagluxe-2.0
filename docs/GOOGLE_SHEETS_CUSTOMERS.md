# Quản lý khách hàng và giao nhận trong Google Sheets

## Cài đặt bản code đầy đủ

1. Sao lưu code Apps Script hiện tại trước khi thay thế.
2. Dán toàn bộ bản mới vào file `Code.gs` của bảng tính đang sử dụng, lưu lại.
3. Tải lại Google Sheets. Trong menu **🚀 TagLuxe Admin**, chọn
   **👤 Bật / Cập nhật quản lý khách hàng**. Hoặc chạy hàm `setupCustomerManagement`
   một lần từ trình chỉnh sửa Apps Script và cấp quyền nếu Google yêu cầu.
4. Cập nhật deployment Web App hiện có sang phiên bản mới để báo giá mới tự có
   công thức và trường mặc định. Giữ nguyên khóa xác thực trong Script Properties.

Không cần chạy `setupFullSystem`. Hàm nâng cấp quản lý khách không xóa các dòng cũ,
không reset checkbox hay trạng thái. Nếu O–AC đã chứa cột riêng, hàm sẽ báo lỗi và
dừng trước khi ghi để người dùng bố trí lại cột trước. Không tự di chuyển dữ liệu.

## Trường mới trong tab QUẢN LÝ BÁO GIÁ

| Cột | Nội dung | Cách sử dụng |
|---|---|---|
| O | Công ty / Tổ chức | Nhập tên đơn vị của khách nếu có |
| P | Địa chỉ giao hàng | Nhập đủ số nhà, đường, phường/xã, tỉnh/thành |
| Q | Người nhận hàng | Có thể khác người đặt |
| R | SĐT người nhận | Định dạng văn bản để giữ số 0 đầu |
| S | Ngày khách cần nhận | Chọn ngày bằng lịch |
| T | Giờ / Khung giờ nhận | Ví dụ: trước 15h hoặc 8h–11h |
| U | Hình thức giao hàng | Giao tận nơi, nhận tại shop, chành xe, khác |
| V | Người phụ trách | Nhập tên người xử lý đơn |
| W | Ngày liên hệ lại | Chọn ngày để theo dõi tư vấn |
| X | Mức ưu tiên | Bình thường, ưu tiên, gấp |
| Y | Tiến độ sản xuất / giao | Chờ duyệt mẫu, sản xuất, đóng gói, giao hàng… |
| Z | Đã thu | Nhập tổng số tiền thực tế đã nhận, không nhập số âm |
| AA | Còn phải thu | Tự tính từ tổng tiền J trừ đã thu Z, tối thiểu 0 |
| AB | Mã vận đơn | Nhập mã của đơn vị giao hàng |
| AC | Ghi chú nội bộ / Yêu cầu đặc biệt | Nội dung trao đổi, yêu cầu đóng gói, xuất hóa đơn… |

Cột N vẫn là dữ liệu khôi phục tự động. Không sửa cột này để nhập địa chỉ.

Ngày cần nhận đến hạn/quá hạn tô đỏ; ngày liên hệ lại đến hạn tô vàng. Bỏ qua báo
giá đã xong/đã hủy hoặc tiến độ đã giao. Công thức nhắc việc dựa trên ngày hiện tại
theo múi giờ của bảng tính, không tự gửi email hay thông báo lịch.

Tiền còn phải thu chưa tính thêm phí vận chuyển nếu phí này chưa nằm trong tổng
tiền ở cột J. Trạng thái sản xuất và trạng thái tư vấn là hai thông tin riêng.

## Giữ dữ liệu khi cập nhật

- Các trường O–AC được nhập trực tiếp trong Google Sheets, theo từng mã báo giá.
  Một khách có nhiều lần đặt có thể có địa chỉ/ngày nhận khác nhau.
- Webhook chỉ sửa A–K và N khi gửi lại mã đã có, không đụng vào O–AC, L hay M.
- Chạy lại hàm nâng cấp không xóa địa chỉ, ngày cần, tiền đã thu, ghi chú đã nhập.
  Công thức AA chỉ bổ sung khi ô trống và chưa có công thức.
- Bộ lọc được mở rộng sang các cột mới; giữ tiêu chí lọc đang có ở các cột cũ.
- Phần đọc báo giá về admin vẫn theo giao thức cũ, không gửi các cột quản lý mới
  về web. Đây là bổ sung quản lý ngay trong bảng tính, chưa phải form thu địa chỉ
  trên website hoặc đồng bộ các trường mới sang admin.

Kiểm thử cục bộ bằng dữ liệu giả; chưa thay đổi bảng tính thật và chưa triển khai
script vào tài khoản Google của shop.
