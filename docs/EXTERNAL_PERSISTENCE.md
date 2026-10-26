# Giữ Render miễn phí, lưu dữ liệu và ảnh ở Supabase

## Dữ liệu được giữ ở đâu

- PostgreSQL (`DATABASE_URL`): sản phẩm, ảnh gắn vào sản phẩm, bảng giá, phụ kiện,
  báo giá, khách hàng suy ra từ báo giá, ghi chú nội bộ, lịch hẹn, nhật ký và hàng đợi.
- Bảng `site_settings`: cấu hình ảnh demo và banner. File JSON cũ được nhập đúng
  một lần nếu khóa cấu hình chưa có; dữ liệu database luôn được ưu tiên về sau.
- Supabase Storage: ảnh sản phẩm/phụ kiện/demo/banner được tải lên từ admin.
  Tên và đường dẫn `/static/uploads/...` vẫn dùng được. Ảnh có sẵn trong code giữ nguyên.
- Google Sheets tiếp tục nhận bản đồng bộ báo giá; không phải nguồn lưu toàn bộ admin.
- `SECRET_KEY` phải cố định trong biến môi trường để phiên đăng nhập ổn định.

## Thiết lập một lần

1. Chủ shop tạo tài khoản/project Supabase Free, chọn vùng gần người dùng.
2. Tạo bucket **public** tên `tagluxe-media`, chỉ dùng cho ảnh công khai của shop.
   Không đặt database, giấy tờ hoặc hồ sơ khách vào bucket này. Không cần cho phép
   anonymous upload: web upload bằng secret key ở backend.
3. Trong Connect, lấy PostgreSQL **Session pooler**, cổng 5432, dùng được với IPv4.
   Dùng mật khẩu database thật thay chỗ trống; ký tự đặc biệt phải được URL-encode.
4. Lấy Project URL và **secret API key** ở phần API Keys. Khóa mới có dạng
   `sb_secret_...`; không dùng publishable key. Chỉ nhập trong `.env` local được bỏ
   qua bởi Git hoặc phần Environment của hosting, không gửi vào chat/code/frontend.
5. Chuẩn bị bản sao dữ liệu đang có, chuyển vào project TRỐNG bằng công cụ bên dưới.
   Chưa đặt DATABASE_URL mới trên Render trước bước chuyển: ứng dụng cũ có thể tự
   tạo dữ liệu mẫu trong database mới và làm mất điều kiện đích trống của công cụ.
6. Sau khi chuyển và đối chiếu xong, cấu hình các biến trên Render, rồi duyệt đẩy code:

```dotenv
DATABASE_URL=<PostgreSQL Session pooler, giữ bí mật>
MEDIA_STORAGE=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<secret API key, giữ bí mật>
SUPABASE_STORAGE_BUCKET=tagluxe-media
SECRET_KEY=<giữ khóa phiên cố định hiện có>
```

Khi bật Supabase trên Render, code yêu cầu có PostgreSQL URL và cấu hình kho ảnh đầy
đủ. Lưu ảnh thất bại thì báo lỗi, không âm thầm ghi ảnh vào ổ tạm. Các bảng do app
tạo được bật RLS; backend dùng kết nối database owner, không thêm quyền đọc cho anon.

## Chuyển dữ liệu hiện có

**Không deploy chỉ để lấy backup nếu chưa có bản sao dữ liệu cũ.** Deploy có thể
thay ổ tạm của máy đang chạy. Bản code cũ chưa có nút xuất đầy đủ SQLite, vì vậy
không khẳng định có thể lấy được toàn bộ database hiện tại chỉ từ giao diện cũ.
CSV báo giá/Google Sheets không chứa đủ toàn bộ admin. Phải đối chiếu bản database
đang có, ảnh và cấu hình trước khi chuyển; phần không còn bản sao không tự khôi phục.

Bản mới có endpoint admin `/admin/system/migration-backup` để xuất các lần sau:
SQLite snapshot khi đang dùng SQLite, ảnh công khai còn ở máy chủ, JSON cấu hình.
Không chứa `.env`/khóa kết nối và không tải ngược toàn bộ ảnh Supabase. Khi đã dùng
PostgreSQL, sao lưu database bằng công cụ PostgreSQL hoặc dịch vụ quản lý riêng.

Công cụ `scripts/migrate_persistent_data.py`:

```powershell
.\.venv\Scripts\python.exe scripts/migrate_persistent_data.py --source backup\source\tagluxe.db
```

Lệnh trên chỉ kiểm tra nguồn và đếm bản ghi, không kết nối/ghi Supabase. Sau khi
cấu hình `.env` local và đã lưu bản sao nguồn, mới chạy với `--apply`, thêm
`--uploads <thư mục ảnh>` và `--settings <thư mục JSON>` nếu có. Không truyền mật
khẩu qua tham số lệnh. Chỉ chấp nhận database đích trống; nguồn mở chỉ đọc. Nhập
database trong một transaction; ảnh đã upload trước khi lỗi có thể còn ở kho ảnh,
lần chạy lại chỉ nhận ảnh trùng khi nội dung giống hệt, không ghi đè ảnh khác.

## Kiểm chứng sau kết nối

Thêm ảnh thử, sửa giá thử, sửa banner → đăng xuất/đăng nhập → restart/redeploy →
đối chiếu lại. Chỉ khi kiểm tra trên dịch vụ thật đạt mới xác nhận hoàn tất chuyển.
Ngày 25/10/2026 đã kiểm chứng trên project thật: đối chiếu từng bản ghi với bản
snapshot đã chuẩn bị, upload và tải lại ảnh, sửa giá/phụ kiện có ảnh từ admin,
tạo application và phiên admin mới rồi đọc lại đúng dữ liệu. Dữ liệu kiểm thử
riêng đã được xóa. 46 bài kiểm thử tự động cũng đạt. Việc này chưa xác nhận
Render đã chuyển sang Supabase: phải cấu hình hosting và deploy bản code mới.

Bản snapshot chuyển lần này gồm 3 sản phẩm, 10 phụ kiện, 44 bậc giá đang dùng,
13 bậc giá tương thích cũ, 18 báo giá và 52 ảnh. Nguồn là các bản xuất chỉ đọc
từ admin/public API đang chạy, không phải bản dump database sản xuất đầy đủ.
Không khôi phục được trạng thái idempotency cũ, lease hàng đợi cũ và IP nhật ký
cũ; không tạo tác vụ gửi lại báo giá khách. Trước khi chuyển web chính thức,
phải đối chiếu thay đổi/báo giá mới phát sinh sau thời điểm snapshot.

## Giới hạn gói miễn phí

Theo Supabase tại thời điểm chuẩn bị: 500 MB database, 1 GB file storage, quota
băng thông và có thể tạm dừng project sau một tuần thiếu hoạt động. Không đồng
nghĩa dịch vụ luôn hoạt động hoặc có backup tự động. Chủ shop cần theo dõi quota,
lưu backup riêng và khôi phục project nếu bị pause.

Nguồn: https://supabase.com/pricing,
https://supabase.com/docs/guides/database/connecting-to-postgres,
https://supabase.com/docs/guides/storage/serving/downloads.
