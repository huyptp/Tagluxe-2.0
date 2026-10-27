# HƯỚNG DẪN KẾT NỐI BÁO GIÁ TAGLUXE VÀO GOOGLE SHEETS

## Khi báo giá vào bảng tính nhưng không có email

Email được gửi bởi Apps Script qua `MailApp`, không phải bởi Supabase. Địa chỉ
nhận nằm trong `NOTIFICATION_EMAIL`. Trạng thái đồng bộ bảng tính của các bản
script cũ không xác nhận email đã gửi thành công.

Bản sửa ngày 26/10/2026 không bỏ qua lỗi gửi mail. Bản ghi mới được đánh dấu
email chờ gửi; nếu Google từ chối vì quyền hoặc hạn mức, webhook trả lỗi và giữ
đánh dấu để lần đồng bộ lại có thể gửi email dù dòng báo giá đã tồn tại.
Sau khi gửi thành công, đánh dấu được xóa để các lần gửi lại thông thường không
gửi trùng. Bản ghi cũ không có đánh dấu sẽ không bị gửi email hàng loạt.

Cập nhật mã trong dự án Apps Script đang dùng, giữ đúng `WEBHOOK_SECRET` hoặc
thuộc tính script cùng tên khớp với `GOOGLE_SHEET_SECRET` trên web. Lưu code chưa
làm thay đổi bản Web app đã triển khai: vào **Triển khai → Quản lý các bản triển
khai → Sửa → Phiên bản mới → Triển khai**, cập nhật chính bản đang dùng để giữ URL.

Để kiểm tra theo yêu cầu của chủ shop: chọn hàm `sendTestNotification` trong
Apps Script rồi chạy, cấp quyền gửi email nếu Google yêu cầu. Bản sửa chỉ hiện
thông báo thành công sau khi MailApp chấp nhận gửi; nếu lỗi, xem mục **Lần thực
thi / Executions**. MailApp chấp nhận gửi không chứng minh thư đã vào Inbox;
cần kiểm tra Gmail gồm Spam và Trash. Không gửi email thật trong kiểm thử tự động.

Tài liệu Google: https://developers.google.com/apps-script/reference/mail/mail-app,
https://developers.google.com/apps-script/concepts/deployments.

Hệ thống cho phép thu thập thông tin khách hàng (Họ tên, SĐT, Số lượng, Bản dây, Phụ kiện, Tổng tiền, Ghi chú) trực tiếp từ website TagLuxe và đồng bộ tự động vào Google Sheets theo thời gian thực.

---

## BƯỚC 1: TẠO BẢNG TÍNH GOOGLE SHEETS

1. Truy cập [https://sheets.new](https://sheets.new) để tạo một Google Sheet mới.
2. Đặt tên file (ví dụ: `TagLuxe - Đơn Báo Giá Khách Hàng`).
3. Bạn không cần tự gõ tiêu đề cột; mã script sẽ tự động tạo hàng tiêu đề chuẩn và định dạng màu sắc chuyên nghiệp ngay khi có đơn đầu tiên gửi về.

---

## BƯỚC 2: CÀI ĐẶT GOOGLE APPS SCRIPT

1. Trên menu trên cùng của Google Sheets, bấm vào:  
   **Tiện ích mở rộng (Extensions)** > **Apps Script**.
2. Xóa toàn bộ đoạn code mẫu có sẵn trong cửa sổ soạn thảo.
3. Mở file [`google_sheets_script.js`](./google_sheets_script.js), sao chép toàn bộ nội dung và dán vào Apps Script.
4. Bấm biểu tượng **Lưu dự án (Save)** (phím tắt `Ctrl + S`).
5. Ở góc trên cùng bên phải, bấm nút **Triển khai (Deploy)** > chọn **Tùy chọn triển khai mới (New deployment)**.
6. Cấu hình triển khai như sau:
   - Bấm vào biểu tượng bánh răng bên cạnh mục *Chọn loại (Select type)* > Chọn **Ứng dụng web (Web app)**.
   - **Mô tả (Description)**: `TagLuxe Quote Webhook`
   - **Thực thi dưới tên (Execute as)**: `Tôi (Me - địa chỉ email của bạn)`
   - **Ai có quyền truy cập (Who has access)**: **`Bất kỳ ai (Anyone)`** *(Lưu ý: Bắt buộc chọn "Bất kỳ ai" để Render Webhook có thể gửi dữ liệu sang mà không bị chặn xác thực)*.
7. Bấm nút **Triển khai (Deploy)**.
8. Google sẽ hiển thị popup yêu cầu quyền:
   - Bấm **Ủy quyền truy cập (Authorize access)**.
   - Chọn tài khoản Google của bạn.
   - Nếu thấy cảnh báo "Google chưa xác minh ứng dụng này", bấm **Nâng cao (Advanced)** > chọn **Đi tới [Tên dự án] (không an toàn)** > Bấm **Cho phép (Allow)**.
9. Sau khi hoàn tất, Google sẽ cấp cho bạn một đường link tại mục **URL ứng dụng web (Web app URL)**, có định dạng:
   ```
   https://script.google.com/macros/s/AKfycbx.../exec
   ```
10. Bấm nút **Sao chép (Copy)** đường link này.

---

## BƯỚC 3: CẤU HÌNH BIẾN MÔI TRƯỜNG TRÊN RENDER

1. Đăng nhập vào [Render Dashboard](https://dashboard.render.com).
2. Bấm vào Web Service dự án TagLuxe của bạn (ví dụ: `tagluxe`).
3. Ở menu bên trái, chọn mục **Environment**.
4. Bấm nút **Add Environment Variable**:
   - **Key**: `GOOGLE_SHEET_WEBHOOK_URL`
   - **Value**: Dán đường link Web app URL bạn vừa sao chép ở Bước 2.
5. Bấm nút **Save Changes**.

Render sẽ tự động tiến hành redeploy lại phiên bản mới nhất. Từ lúc này, mỗi khi khách hàng tính phí và gửi thông tin trên website, dữ liệu sẽ tự động được ghi nhận ngay lập tức vào Google Sheets của bạn!

---

## KIỂM TRA THỬ NGHIỆM TRÊN MÁY LOCAL

Nếu muốn test ngay trên máy tính của bạn trước khi đưa lên Render:
1. Mở terminal PowerShell tại thư mục dự án và chạy:
   ```powershell
   $env:GOOGLE_SHEET_WEBHOOK_URL="<dán_link_webhook_của_bạn_vào_đây>"
   python app.py
   ```
2. Truy cập [http://127.0.0.1:5000/#calculator](http://127.0.0.1:5000/#calculator)
3. Điền thông tin thử và bấm **GỬI LƯU BÁO GIÁ & NHẬN DEMO**.
4. Mở Google Sheets kiểm tra: dòng dữ liệu mới sẽ xuất hiện ngay lập tức!
