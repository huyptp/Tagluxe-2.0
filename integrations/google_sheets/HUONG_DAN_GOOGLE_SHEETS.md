# HƯỚNG DẪN KẾT NỐI BÁO GIÁ TAGLUXE VÀO GOOGLE SHEETS

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
