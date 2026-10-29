# Cải thiện UX/UI admin — 29/10/2026

## Nguồn tham khảo đã tải

- Tabler: https://github.com/tabler/tabler — bố cục admin, nhóm điều hướng, mật độ bảng và trạng thái form.
- Radix Themes: https://github.com/radix-ui/themes — hệ thống kích thước, kiểu chữ, trạng thái control và focus.
- W3C target size: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html — điểm bấm và khoảng cách.

Hai bản ZIP đầy đủ và các file CSS/SCSS được chọn để đọc nằm trong `backup/ux-ui-references-20261029/`. `manifest.json` ghi commit chính xác và danh sách file tham khảo; giấy phép gốc giữ trong thư mục từng dự án. Không chạy mã tải về, không thêm framework vào app, không sao chép nguyên component. CSS triển khai là CSS riêng của TAGLUXE.

## Các thay đổi

`workspace.css` là lớp giao diện chung nạp sau CSS admin hiện có để thống nhất chữ, màu, control, bảng, form và kích thước tương tác. Chữ phụ tăng độ tương phản, chữ nhập trên điện thoại dùng 16px, nút chính có chiều cao tối thiểu 44px trên màn hình nhỏ. Đây là cải thiện có mục tiêu, chưa phải chứng nhận toàn bộ ứng dụng đạt WCAG.

Báo giá có lối tắt Tất cả / Mới nhận / Đang tư vấn / Đến hẹn. Tìm kiếm, trạng thái, sắp xếp luôn hiện; các bộ lọc ít dùng gom vào details. Details tự mở khi có bộ lọc nâng cao được áp dụng và giữ nguyên tên tham số GET cũ. Trên điện thoại, bảng báo giá chuyển thành thẻ.

Cập nhật hàng loạt giữ bước xác nhận cũ, chỉ cho bấm khi đã chọn báo giá và trạng thái. Dòng đã chọn có nền riêng, nhãn nút nêu số lượng. Không gửi dữ liệu khi chỉ chọn/bỏ chọn.

Trạng thái có cả chữ và màu bổ trợ. Sao chép SĐT có thông báo, form khách có dấu Chưa lưu, menu điện thoại hỗ trợ xoay vòng Tab và Escape trả focus về nút menu. Phím `/` đưa focus vào tìm khách nhanh nếu ô đang hiện. Nút gửi được khôi phục khi quay lại trang từ bộ nhớ trình duyệt.

## Kiểm tra

56 kiểm thử Python hiện có cho CRM, phân quyền, báo giá, xóa khách và bill; JavaScript kiểm tra cú pháp. Kiểm tra trình duyệt bằng khách mẫu tách biệt: desktop 1440px, mobile 390px; chọn/bỏ chọn báo giá; menu mở/Escape; bảng báo giá không làm tràn ngang toàn trang. Chưa thực hiện kiểm thử với người dùng hoặc rà toàn bộ tiêu chí WCAG.

Các thay đổi CRM của lượt trước vẫn giữ nguyên, chưa đẩy GitHub cho đến khi người dùng duyệt cả bản.
