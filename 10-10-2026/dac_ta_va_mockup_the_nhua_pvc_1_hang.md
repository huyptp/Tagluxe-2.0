# ĐẶC TẢ KỸ THUẬT & BẢN THIẾT KẾ MOCKUP: HIỂN THỊ ẢNH THỰC TẾ THẺ NHỰA PVC 1 HÀNG

**Dự án:** TagLuxe 2.0 — Website Sản Xuất & Bán Sỉ Dây Đeo Thẻ, Thẻ Nhựa PVC & Phụ Kiện  
**Ngày thực hiện:** 10/10/2026  
**Trạng thái:** Đang chờ người dùng phê duyệt Mockup (Rule 12)  

---

## 1. MỤC TIÊU & TỔNG QUAN THAY ĐỔI

Theo yêu cầu của người dùng, giao diện hiển thị ảnh thực tế của danh mục **Thẻ Nhựa PVC** (`#the-nhua-pvc`) sẽ được chuyển từ dạng băng chuyền chạy tự động 2 hàng đối xứng sang dạng **1 hàng trượt ngang thủ công (Horizontal Scroll Gallery)**, tạo sự nhất quán và trải nghiệm đồng bộ 100% với mục **Vỏ Đựng Thẻ (Card Holder)** (`#vo-dung-the`).

### Bảng So sánh Trực quan (Trước & Sau)

| Tiêu chí | Phiên bản Hiện tại (Trước) | Phiên bản Đề xuất Mới (Sau) | Lợi ích Trải nghiệm (UX) |
| :--- | :--- | :--- | :--- |
| **Bố cục hàng** | 2 hàng chạy song song đối xứng | **1 hàng duy nhất** | Gọn gàng, tập trung thị giác, không gây rối mắt |
| **Cơ chế chuyển động** | Tự động chạy ngang ngược chiều liên tục (`marquee infinite`) | **Trượt ngang thủ công (Scroll/Drag)** | Người dùng chủ động lướt xem từng mẫu theo nhịp độ mong muốn |
| **Tương tác Desktop** | Rê chuột tạm dừng (`hover: pause`) | Kéo thả chuột (`cursor: grab / grabbing`), cuộn lăn chuột hoặc thanh trượt thanh thoát | Cảm giác tương tác trực tiếp, chân thực như thư viện ảnh cao cấp |
| **Tương tác Mobile** | Vuốt trôi tự động | Vuốt chạm tự nhiên mượt mà (`touch-scroll`, `-webkit-overflow-scrolling: touch`) | Thân thiện tuyệt đối với thao tác ngón cái trên smartphone |
| **Số lượng hiển thị** | 6 ảnh lặp lại 4 lần (24 items) | **Hiển thị đúng 6 ảnh thực tế gốc** | Trung thực, rõ ràng, không lặp lại ảnh ảo |
| **Sự đồng bộ hệ thống** | Giống mục Dây đeo thẻ | **Đồng nhất 100% với mục Vỏ đựng thẻ** | Kiến trúc giao diện phân cấp rõ ràng: Dây đeo (2 hàng chạy) - Thẻ PVC & Vỏ thẻ (1 hàng trượt ngang) |

---

## 2. WIREFRAME MOCKUP BỐ CỤC GIAO DIỆN STOREFRONT

```
====================================================================================================
                        IN THẺ NHỰA PVC THEO YÊU CẦU (SECTION #the-nhua-pvc)
====================================================================================================

      [Tiêu đề]: In Thẻ Nhựa PVC Theo Yêu Cầu
      [Mô tả]:   Chất liệu PVC 4 lớp cao cấp chuẩn ISO 7810, độ bền vượt trội, màu sắc chuẩn xác.

+--------------------------------------------------------------------------------------------------+
| < [Kéo chuột hoặc Vuốt sang để xem thêm mẫu thẻ thực tế] >                                       |
|                                                                                                  |
|  +--------------+  +--------------+  +--------------+  +--------------+  +--------------+ ...    |
|  | [ẢNH THỰC 1] |  | [ẢNH THỰC 2] |  | [ẢNH THỰC 3] |  | [ẢNH THỰC 4] |  | [ẢNH THỰC 5] |        |
|  | Thẻ PVC bo   |  | Thẻ nhân viên|  | Thẻ hội viên |  | Thẻ chip NFC |  | Thẻ VIP mạ   |        |
|  | góc 4 lớp    |  | dập nổi      |  | 4 lớp sắc nét|  | cảm ứng      |  | kim nhũ vàng |        |
|  |              |  |              |  |              |  |              |  |              |        |
|  | [Xem chi tiết|  | [Xem chi tiết|  | [Xem chi tiết|  | [Xem chi tiết|  | [Xem chi tiết|        |
|  |       ->]    |  |       ->]    |  |       ->]    |  |       ->]    |  |       ->]    |        |
|  +--------------+  +--------------+  +--------------+  +--------------+  +--------------+ ...    |
|  ===================================[ Thanh cuộn mảnh xám ]======================================|
+--------------------------------------------------------------------------------------------------+

            [ 💬 Tư vấn & Đặt hàng ngay (Zalo) ]     [ 🧮 Bảng tính giá thẻ PVC ]
```

---

## 3. SO SÁNH ĐỒNG BỘ 2 KHỐI "THẺ NHỰA PVC" VÀ "VỎ ĐỰNG THẺ"

```
[KHỐI THẺ NHỰA PVC (#the-nhua-pvc)]                 [KHỐI VỎ ĐỰNG THẺ (#vo-dung-the)]
+------------------------------------------+        +------------------------------------------+
|  .lanyard-gallery-container              |        |  .lanyard-gallery-container              |
|    .gallery-scroll-box#pvcGalleryBox     |        |    .gallery-scroll-box#holderGalleryBox  |
|      .gallery-scroll-row (1 hàng ngang)  |  ===>  |      .gallery-scroll-row (1 hàng ngang)  |
|        [Card 1] [Card 2] [Card 3]...     |        |        [Card 1] [Card 2] [Card 3]...     |
+------------------------------------------+        +------------------------------------------+
  -> Cùng dùng class CSS:                              -> Đang chạy ổn định, giao diện mượt mà:
     - .lanyard-gallery-container                         - Hiển thị 6 mẫu vỏ ABS/Silicon
     - .gallery-scroll-box                                - Nút "Xem chi tiết ->"
     - .gallery-scroll-row                                - Thanh scrollbar bo tròn 999px
     - .lanyard-marquee-card
```

---

## 4. CHI TIẾT CẤU TRÚC CODE THAY THẾ (DROP-IN REPLACEMENT)

### Mã HTML mới trong `frontend/storefront/templates/index.html` & `templates/index.html`:

```html
<!-- ===== THẺ NHỰA PVC ===== -->
<section id="the-nhua-pvc" class="section" aria-label="In thẻ nhựa PVC theo yêu cầu">
    <div id="accessories" style="position:relative; top:-80px;"></div>
    <div class="container">
        <div class="section-header" data-aos="fade-up">
            <h2>In Thẻ Nhựa PVC Theo Yêu Cầu</h2>
        </div>

        <!-- Mẫu thẻ nhựa PVC thực tế (1 hàng trượt thủ công giống vỏ thẻ) -->
        {% set pvc_imgs = (pvc_product.images if pvc_product and pvc_product.images else []) %}
        {% if pvc_imgs %}
        <div class="lanyard-gallery-container" data-aos="fade-up">
            <div class="gallery-scroll-box" id="pvcGalleryBox">
                <div class="gallery-scroll-row">
                    {% for img in pvc_imgs %}
                    <a href="/product/{{ pvc_product.id if pvc_product else 'acc-1' }}" class="lanyard-marquee-card" aria-label="{{ pvc_product.name if pvc_product else 'Thẻ nhựa PVC' }}">
                        <div class="lanyard-card-img">
                            <img src="{{ url_for('static', filename='uploads/' + img) }}?v={{ asset_v }}"
                                 alt="Mẫu thẻ nhựa PVC {{ loop.index }} - TagLuxe" loading="lazy">
                        </div>
                        <div class="lanyard-card-body">
                            <span class="lanyard-card-name">{{ pvc_product.name if pvc_product else 'Thẻ nhựa PVC' }}</span>
                            <span class="lanyard-card-action">Xem chi tiết <i data-lucide="arrow-right"></i></span>
                        </div>
                    </a>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}

        <div class="text-center" style="margin-top:36px;" data-aos="fade-up">
            <a href="https://zalo.me/0343019097" target="_blank" rel="noopener" class="btn btn-primary" style="font-size:1.05rem; padding:14px 32px;">
                <i data-lucide="message-circle"></i> Tư vấn & Đặt hàng ngay
            </a>
            <a href="#calculator" onclick="if(window.switchCategory) switchCategory('pvc');" class="btn btn-outline" style="font-size:1.05rem; padding:14px 28px; margin-left:12px;">
                <i data-lucide="calculator"></i> Bảng tính giá thẻ PVC
            </a>
        </div>
    </div>
</section>
```

---

## 5. KẾ HOẠCH BÀN GIAO & DUYỆT THIẾT KẾ (RULE 12)

1. **Bước 1:** Trình bày UI Mockup trực quan để người dùng phê duyệt.
2. **Bước 2 (Sau khi duyệt):** Cập nhật mã nguồn `frontend/storefront/templates/index.html` và `templates/index.html`.
3. **Bước 3:** Đồng bộ sang kho chính `D:\Antigravity\TAGLUXE`.
4. **Bước 4:** Chạy kiểm thử tự động toàn diện và kiểm tra giao diện trên server thực tế.
