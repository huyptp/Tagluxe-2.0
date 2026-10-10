# TagLuxe — Google indexing

Website chính được chủ sở hữu chọn: https://tagluxe.onrender.com/

## Kết quả ngày 14/09/2026

- Ảnh Search Console ban đầu ghi nhận Googlebot trên điện thoại gặp lỗi máy chủ 5xx. Thu thập dữ liệu được cho phép.
- Ảnh kiểm tra phiên bản hoạt động lúc 10:16 báo **Google có thể lập chỉ mục URL này**.
- Gửi yêu cầu lập chỉ mục bị chặn bởi hạn ngạch hằng ngày; hộp thoại đề nghị thử lại ngày mai. Không có bằng chứng URL đã được lập chỉ mục.
- Website dùng Render Free (chủ sở hữu xác nhận). Free có thể ngủ sau 15 phút không có truy cập; cần khoảng một phút khởi động. Chưa có log để kết luận lần 5xx trước chắc chắn do ngủ.

## Cấu hình trong mã nguồn

- Trang chủ và các sản phẩm công khai xuất HTML từ máy chủ, có title, description và canonical.
- `SITE_URL` là nguồn cấu hình chung cho canonical, Open Graph, JSON-LD, robots và sitemap. Mặc định là URL Render trên; khi có tên miền riêng, cấu hình HTTPS origin mới.
- `/sitemap.xml` gồm trang chủ, sản phẩm đang hiển thị và ảnh sản phẩm. XML được tạo bằng bộ mã hóa XML; tên tệp đặc biệt được mã hóa URL. Không giả định nội dung được sửa mỗi ngày.
- `/robots.txt` cho phép phần website khách hàng và khai báo sitemap. Trang quản trị, health check và trang lỗi có header `X-Robots-Tag: noindex, nofollow`.
- Schema sản phẩm chỉ khai báo giá khi sản phẩm có giá cố định thực tế. Sản phẩm liên hệ báo giá không khai báo giá thay thế. Không tạo đánh giá hay số lượt đánh giá giả.
- Mã xác minh Search Console vẫn lấy từ `GOOGLE_SITE_VERIFICATION` trên Render. Không đổi mã này khi triển khai.

## Việc tiếp theo trong Search Console

1. Chọn thuộc tính `https://tagluxe.onrender.com/`.
2. Vào **Sơ đồ trang web**. Nếu chưa gửi, nhập `sitemap.xml` và gửi một lần. Nếu đã gửi, kiểm tra trạng thái thay vì gửi lặp lại.
3. Khi hạn ngạch cho phép (thông báo hiện tại đề nghị ngày mai), kiểm tra URL trang chủ rồi chọn **Yêu cầu lập chỉ mục** một lần.
4. Theo dõi báo cáo Trang và Kiểm tra URL. Chỉ xác nhận đã lập chỉ mục khi Google báo URL nằm trên Google.
5. Nếu 5xx quay lại, đối chiếu thời điểm lỗi với Render Events/Logs: khởi động, deploy, timeout, thiếu bộ nhớ hoặc lỗi ứng dụng. Không suy luận mọi 5xx đều do gói Free.

## Trước khi chạy ads

Render Free phù hợp thử nghiệm; cân nhắc dịch vụ không ngủ để khách quảng cáo và Google nhận phản hồi ổn định. Đổi sang gói trả phí là một quyết định chi phí riêng, cần chủ sở hữu thực hiện hoặc cho phép.

Render dùng filesystem tạm thời. Danh mục `data.json` và ảnh cập nhật trong quản trị phải được sao lưu trước khi redeploy/restart; nâng gói riêng lẻ không tự làm chúng bền vững nếu chưa cấu hình persistent disk hoặc kho dữ liệu ngoài. Trước đợt sửa SEO này đã đối chiếu 5 sản phẩm và 22 ảnh trên máy chủ với bản nguồn tại máy, khớp cả nội dung ảnh.

Trang quản trị hiện còn cấu hình đăng nhập mặc định trong nguồn cũ. Cần chuyển thông tin xác thực và khóa phiên sang biến môi trường an toàn trước khi vận hành thương mại; không đưa thông tin đăng nhập vào tài liệu hoặc nội dung website.

## Kiểm tra thay đổi

Chạy `python -m unittest test_seo -v`. Bộ kiểm tra bao gồm metadata JSON hợp lệ, ký tự đặc biệt, giá thật/giá liên hệ, sitemap chỉ chứa sản phẩm hiển thị, tên miền cấu hình đồng nhất, và noindex cho trang quản trị/lỗi.

Nguồn chính thức:

- https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl
- https://developers.google.com/crawling/docs/troubleshooting/http-status-codes
- https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- https://render.com/docs/free
