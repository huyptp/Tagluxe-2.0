/**
 * ==============================================================================
 * GOOGLE APPS SCRIPT: TAGLUXE ADMIN & SHOP OPERATIONS DASHBOARD + EMAIL NOTIFIER
 * Phiên bản chuẩn hóa: Tích Tiến độ Checkbox, Đang tư vấn, Đã tư vấn, Đang chốt, Đã chốt, Đã xong
 * ==============================================================================
 */

// CẤU HÌNH NHẬN EMAIL (Gửi thông báo về Gmail của chủ Shop)
var NOTIFICATION_EMAIL = "Dhuy5585@gmail.com"; 


// Danh sách các nấc Trạng thái xử lý chuẩn của TagLuxe
var ORDER_STATUSES = [
  "Mới",
  "Đang tư vấn",
  "Đã tư vấn",
  "Đang chốt",
  "Đã chốt",
  "Đã xong",
  "Đã hủy"
];

// Bảng màu cho từng trạng thái
var STATUS_COLORS = [
  { text: "Mới", bg: "#fef3c7", fg: "#92400e" },          // Vàng nhạt
  { text: "Đang tư vấn", bg: "#e0f2fe", fg: "#0369a1" },  // Xanh dương
  { text: "Đã tư vấn", bg: "#ccfbf1", fg: "#0f766e" },    // Xanh mòng két
  { text: "Đang chốt", bg: "#ffedd5", fg: "#c2410c" },    // Cam nhạt
  { text: "Đã chốt", bg: "#f3e8ff", fg: "#7e22ce" },      // Tím
  { text: "Đã xong", bg: "#dcfce7", fg: "#15803d" },      // Xanh lá
  { text: "Đã hủy", bg: "#fee2e2", fg: "#b91c1c" }        // Đỏ nhạt
];

var THEME = {
  NAVY: "#0a192f",
  NAVY_LIGHT: "#172a45",
  GOLD: "#d4af37",
  WHITE: "#ffffff",
  CARD_BLUE: "#e0f2fe",
  TEXT_BLUE: "#0369a1",
  CARD_YELLOW: "#fef3c7",
  TEXT_YELLOW: "#92400e",
  CARD_GREEN: "#dcfce7",
  TEXT_GREEN: "#166534",
  CARD_PURPLE: "#f3e8ff",
  TEXT_PURPLE: "#6b21a8"
};

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("🚀 TagLuxe Admin")
    .addItem("📊 Khởi tạo / Làm mới Giao diện Dashboard", "setupFullSystem")
    .addItem("🎨 Dọn dẹp Hộp kiểm & Cài đặt Menu Trạng thái", "setupStatusDropdownsAndColors")
    .addItem("➕ Thêm Thử 1 Đơn Mẫu Trực Tiếp Vào Bảng", "addSampleQuoteRow")
    .addItem("✉️ Gửi Thử 1 Email Thông Báo Test", "sendTestNotification")
    .addToUi();
}


// CẤU HÌNH BẢO MẬT WEBHOOK SECRET (Khớp với GOOGLE_SHEET_SECRET trên server)
var WEBHOOK_SECRET = ""; 

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // Kiểm tra Secret key bảo mật nếu được cấu hình
    var scriptSecret = WEBHOOK_SECRET || PropertiesService.getScriptProperties().getProperty("WEBHOOK_SECRET");
    if (scriptSecret) {
      var incomingSecret = data.secret || (e.parameter && e.parameter.secret);
      if (incomingSecret !== scriptSecret) {
        return ContentService
          .createTextOutput(JSON.stringify({ status: "error", message: "Unauthorized: Invalid or missing webhook secret key" }))
          .setMimeType(ContentService.MimeType.JSON);
      }
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    ensureSheetsExist(ss);

    var isDemo = data.category && data.category.indexOf("Demo") !== -1;
    if (isDemo) {
      saveDemoRequest(ss, data);
    } else {
      saveQuoteOrder(ss, data);
    }

    // Gửi Email thông báo tức thời
    sendEmailNotification(data, isDemo, ss.getUrl());

    return ContentService
      .createTextOutput(JSON.stringify({ status: "success", message: "Đã ghi nhận và gửi email thành công!" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function sendEmailNotification(data, isDemo, sheetUrl) {
  try {
    var recipient = NOTIFICATION_EMAIL || Session.getEffectiveUser().getEmail();
    if (!recipient) return;

    var customerName = data.customer_name || "Khách hàng ẩn danh";
    var phone = String(data.phone || "").trim();
    var rawDigits = phone.replace(/[^0-9]/g, "");
    var zaloUrl = rawDigits ? "https://zalo.me/" + rawDigits : "#";
    var callUrl = rawDigits ? "tel:" + rawDigits : "#";

    var subject = "";
    var badgeTitle = "";
    var mainColor = THEME.NAVY;

    if (isDemo) {
      subject = "🎨 [TagLuxe Demo 2D] Khách mới yêu cầu thiết kế: " + customerName + " (" + phone + ")";
      badgeTitle = "YÊU CẦU PHỐI CẢNH LOGO 2D";
      mainColor = "#0284c7";
    } else {
      var totalMoneyStr = data.total_price ? (data.total_price).toLocaleString("vi-VN") + " đ" : "Liên hệ báo giá";
      subject = "🔔 [TagLuxe Đơn Mới] " + customerName + " vừa gửi báo giá " + totalMoneyStr;
      badgeTitle = "ĐƠN TÍNH GIÁ TRỰC TUYẾN";
      mainColor = "#0a192f";
    }

    var html = `
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
      <div style="background: ${mainColor}; padding: 24px 20px; text-align: center; color: #ffffff;">
        <span style="background: rgba(255,255,255,0.15); color: #d4af37; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase;">${badgeTitle}</span>
        <h2 style="margin: 10px 0 4px; font-size: 20px; color: #ffffff;">CÓ KHÁCH HÀNG MỚI ĐỂ LẠI THÔNG TIN!</h2>
        <p style="margin: 0; font-size: 13px; color: #94a3b8;">Hệ thống website TagLuxe vừa ghi nhận lúc ${data.created_at || 'vừa xong'}</p>
      </div>

      <div style="padding: 24px 20px; background: #ffffff;">
        <div style="background: #f1f5f9; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr>
              <td style="padding: 6px 0; color: #64748b; width: 130px;">👤 Họ tên khách:</td>
              <td style="padding: 6px 0; font-weight: bold; color: #0f172a; font-size: 15px;">${customerName}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0; color: #64748b;">📞 Số điện thoại:</td>
              <td style="padding: 6px 0;">
                <a href="${callUrl}" style="color: #0284c7; text-decoration: none; font-weight: bold; font-size: 15px;">${phone}</a>
              </td>
            </tr>
            <tr>
              <td style="padding: 6px 0; color: #64748b;">📦 Sản phẩm:</td>
              <td style="padding: 6px 0; font-weight: bold; color: #334155;">${data.category || 'Dây đeo thẻ'}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0; color: #64748b;">🔢 Số lượng:</td>
              <td style="padding: 6px 0; font-weight: bold; color: #0f172a;">${data.quantity || 0}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0; color: #64748b;">📐 Quy cách:</td>
              <td style="padding: 6px 0; color: #334155;">${data.specs || data.width || 'Mặc định'}</td>
            </tr>
            ${!isDemo && data.accessories && data.accessories.length > 0 ? `
            <tr>
              <td style="padding: 6px 0; color: #64748b;">📎 Phụ kiện:</td>
              <td style="padding: 6px 0; color: #334155;">${Array.isArray(data.accessories) ? data.accessories.join(', ') : data.accessories}</td>
            </tr>
            ` : ''}
            ${!isDemo ? `
            <tr>
              <td style="padding: 8px 0; color: #64748b; border-top: 1px dashed #cbd5e1;">💰 Tổng chi phí:</td>
              <td style="padding: 8px 0; font-weight: 800; color: #b45309; font-size: 18px; border-top: 1px dashed #cbd5e1;">${(data.total_price || 0).toLocaleString('vi-VN')} đ</td>
            </tr>
            ` : ''}
            ${data.notes ? `
            <tr>
              <td style="padding: 6px 0; color: #64748b; vertical-align: top;">📝 Ghi chú:</td>
              <td style="padding: 6px 0; color: #475569; font-style: italic;">${data.notes}</td>
            </tr>
            ` : ''}
          </table>
        </div>

        <div style="text-align: center; margin: 20px 0 10px;">
          ${rawDigits ? `
          <a href="${zaloUrl}" target="_blank" style="display: inline-block; background: #0068ff; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px; margin-right: 8px; margin-bottom: 8px;">
            💬 Bấm Nhắn Zalo Cho Khách Ngay
          </a>
          ` : ''}
          <a href="${sheetUrl}" target="_blank" style="display: inline-block; background: #0a192f; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px; margin-bottom: 8px;">
            📊 Mở Bảng Google Sheet
          </a>
        </div>
      </div>
      <div style="padding: 14px 20px; background: #f1f5f9; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
        Thông báo tự động từ Hệ thống TagLuxe Website &copy; 2026.
      </div>
    </div>
    `;

    MailApp.sendEmail({ to: recipient, subject: subject, htmlBody: html });
  } catch (err) {
    console.error("[EMAIL_NOTIFY_ERROR] " + err.toString());
  }
}

function sendTestNotification() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var mockData = {
    customer_name: "Nguyễn Văn Test",
    phone: "0912345678",
    category: "Dây đeo thẻ Lụa Satin",
    quantity: 50,
    specs: "Bản 2.0cm",
    accessories: ["Khóa an toàn sau gáy"],
    total_price: 1425000,
    notes: "Đây là email thử nghiệm tính năng thông báo!",
    created_at: new Date().toLocaleString("vi-VN")
  };
  sendEmailNotification(mockData, false, ss.getUrl());
  SpreadsheetApp.getUi().alert("Đã gửi email thông báo thử nghiệm thành công! Bạn hãy mở hộp thư Gmail lên kiểm tra nhé.");
}

function setupFullSystem() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureSheetsExist(ss);
  setupDashboardSheet(ss);
  setupQuotesSheet(ss);
  setupDemoSheet(ss);
  setupStatusDropdownsAndColors();
  SpreadsheetApp.flush();
}

function ensureSheetsExist(ss) {
  var sheets = ["📊 DASHBOARD TỔNG QUAN", "📋 QUẢN LÝ BÁO GIÁ", "🎨 YÊU CẦU DEMO 2D"];
  for (var i = 0; i < sheets.length; i++) {
    if (!ss.getSheetByName(sheets[i])) {
      ss.insertSheet(sheets[i], i);
    }
  }
}

function getFormulaSep(ss) {
  var locale = (ss.getSpreadsheetLocale() || "").toLowerCase();
  // Ở Việt Nam và các nước dùng dấu phẩy cho thập phân thì hàm ngăn cách bằng dấu chấm phẩy ;
  if (locale.indexOf("en_us") !== -1 || locale === "en") {
    return ",";
  }
  return ";";
}

function setupDashboardSheet(ss) {
  var sheet = ss.getSheetByName("📊 DASHBOARD TỔNG QUAN");
  sheet.clear();
  sheet.setTabColor(THEME.GOLD);
  sheet.setHiddenGridlines(false);

  var sep = getFormulaSep(ss);

  sheet.getRange("A1:K1").merge().setValue("🌟 TAGLUXE SOCIAL COMMERCE - TRUNG TÂM VẬN HÀNH & BÁO GIÁ")
       .setBackground(THEME.NAVY).setFontColor(THEME.WHITE).setFontWeight("bold").setFontSize(13).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(1, 45);

  sheet.getRange("A2:K2").merge().setValue("Hệ thống tự động cập nhật thời gian thực khi có khách đặt in trên website")
       .setBackground("#0f2744").setFontColor("#94a3b8").setFontStyle("italic").setFontSize(9).setHorizontalAlignment("center");
  sheet.setRowHeight(2, 24);

  // 4 Thẻ KPI
  // 1. Tổng đơn
  sheet.getRange("B4:C4").merge().setValue("📦 TỔNG ĐƠN BÁO GIÁ").setBackground(THEME.CARD_BLUE).setFontColor(THEME.TEXT_BLUE).setFontWeight("bold").setFontSize(9).setHorizontalAlignment("center");
  sheet.getRange("B5:C6").merge().setFormula("=COUNTA('📋 QUẢN LÝ BÁO GIÁ'!A2:A)").setBackground(THEME.CARD_BLUE).setFontColor(THEME.TEXT_BLUE).setFontWeight("bold").setFontSize(22).setHorizontalAlignment("center").setVerticalAlignment("middle");

  // 2. Đang tư vấn & chốt
  sheet.getRange("D4:E4").merge().setValue("⏳ ĐANG TƯ VẤN / CHỐT").setBackground(THEME.CARD_YELLOW).setFontColor(THEME.TEXT_YELLOW).setFontWeight("bold").setFontSize(9).setHorizontalAlignment("center");
  sheet.getRange("D5:E6").merge().setFormula("=COUNTIF('📋 QUẢN LÝ BÁO GIÁ'!M2:M" + sep + " \"*tư vấn*\") + COUNTIF('📋 QUẢN LÝ BÁO GIÁ'!M2:M" + sep + " \"Đang chốt\")").setBackground(THEME.CARD_YELLOW).setFontColor(THEME.TEXT_YELLOW).setFontWeight("bold").setFontSize(22).setHorizontalAlignment("center").setVerticalAlignment("middle");

  // 3. Đã chốt & Đã xong
  sheet.getRange("F4:G4").merge().setValue("🤝 ĐÃ CHỐT & ĐÃ XONG").setBackground(THEME.CARD_GREEN).setFontColor(THEME.TEXT_GREEN).setFontWeight("bold").setFontSize(9).setHorizontalAlignment("center");
  sheet.getRange("F5:G6").merge().setFormula("=COUNTIF('📋 QUẢN LÝ BÁO GIÁ'!M2:M" + sep + " \"Đã chốt\") + COUNTIF('📋 QUẢN LÝ BÁO GIÁ'!M2:M" + sep + " \"Đã xong\")").setBackground(THEME.CARD_GREEN).setFontColor(THEME.TEXT_GREEN).setFontWeight("bold").setFontSize(22).setHorizontalAlignment("center").setVerticalAlignment("middle");

  // 4. Doanh số dự kiến
  sheet.getRange("H4:J4").merge().setValue("💰 DOANH SỐ DỰ KIẾN (VNĐ)").setBackground(THEME.CARD_PURPLE).setFontColor(THEME.TEXT_PURPLE).setFontWeight("bold").setFontSize(9).setHorizontalAlignment("center");
  sheet.getRange("H5:J6").merge().setFormula("=SUM('📋 QUẢN LÝ BÁO GIÁ'!J2:J)").setBackground(THEME.CARD_PURPLE).setFontColor(THEME.TEXT_PURPLE).setFontWeight("bold").setFontSize(18).setHorizontalAlignment("center").setVerticalAlignment("middle").setNumberFormat("#,##0 \"đ\"");

  sheet.getRange("B4:C6").setBorder(true, true, true, true, false, false, "#bae6fd", SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange("D4:E6").setBorder(true, true, true, true, false, false, "#fde68a", SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange("F4:G6").setBorder(true, true, true, true, false, false, "#bbf7d0", SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange("H4:J6").setBorder(true, true, true, true, false, false, "#e9d5ff", SpreadsheetApp.BorderStyle.SOLID);

  // Thống kê theo Dòng sản phẩm
  sheet.getRange("B8:J8").merge().setValue("📈 THỐNG KÊ CHI TIẾT THEO DÒNG SẢN PHẨM").setBackground(THEME.NAVY).setFontColor(THEME.WHITE).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("left");
  sheet.setRowHeight(8, 28);

  sheet.getRange("B9").setValue("STT");
  sheet.getRange("C9:D9").merge().setValue("Dòng Sản Phẩm");
  sheet.getRange("E9:F9").merge().setValue("Số Lượng Đơn");
  sheet.getRange("G9:I9").merge().setValue("Tổng Doanh Số (VNĐ)");
  sheet.getRange("J9").setValue("Tỷ Trọng");
  sheet.getRange("B9:J9").setBackground("#e2e8f0").setFontWeight("bold").setFontColor("#334155").setHorizontalAlignment("center");

  var categories = [
    { stt: 1, name: "Dây đeo thẻ (Lanyards)", filter: "*Dây*" },
    { stt: 2, name: "Thẻ nhựa PVC (ID Cards)", filter: "*PVC*" },
    { stt: 3, name: "Vỏ đựng thẻ ABS", filter: "*Vỏ*" },
    { stt: 4, name: "Combo trọn bộ (Dây + Thẻ + Vỏ)", filter: "*Combo*" }
  ];

  for (var c = 0; c < categories.length; c++) {
    var r = 10 + c;
    sheet.getRange("B" + r).setValue(categories[c].stt).setHorizontalAlignment("center");
    sheet.getRange("C" + r + ":D" + r).merge().setValue(categories[c].name).setFontWeight("500");
    sheet.getRange("E" + r + ":F" + r).merge().setFormula("=COUNTIF('📋 QUẢN LÝ BÁO GIÁ'!C2:C" + sep + " \"" + categories[c].filter + "\")").setHorizontalAlignment("center");
    sheet.getRange("G" + r + ":I" + r).merge().setFormula("=SUMIF('📋 QUẢN LÝ BÁO GIÁ'!C2:C" + sep + " \"" + categories[c].filter + "\"" + sep + " '📋 QUẢN LÝ BÁO GIÁ'!J2:J)").setNumberFormat("#,##0 \"đ\"").setHorizontalAlignment("right");
    sheet.getRange("J" + r).setFormula("=IF(COUNTA('📋 QUẢN LÝ BÁO GIÁ'!A2:A)=0" + sep + " 0" + sep + " E" + r + "/COUNTA('📋 QUẢN LÝ BÁO GIÁ'!A2:A))").setNumberFormat("0.0%").setHorizontalAlignment("center");
    sheet.setRowHeight(r, 26);
  }



  sheet.getRange("B14:D14").merge().setValue("TỔNG CỘNG").setFontWeight("bold").setHorizontalAlignment("center").setBackground("#f1f5f9");
  sheet.getRange("E14:F14").merge().setFormula("=SUM(E10:E13)").setFontWeight("bold").setHorizontalAlignment("center").setBackground("#f1f5f9");
  sheet.getRange("G14:I14").merge().setFormula("=SUM(G10:G13)").setFontWeight("bold").setHorizontalAlignment("right").setNumberFormat("#,##0 \"đ\"").setBackground("#f1f5f9");
  sheet.getRange("J14").setFormula("=SUM(J10:J13)").setFontWeight("bold").setHorizontalAlignment("center").setNumberFormat("0.0%").setBackground("#f1f5f9");
  sheet.getRange("B9:J14").setBorder(true, true, true, true, true, true, "#cbd5e1", SpreadsheetApp.BorderStyle.SOLID);
}

function setupQuotesSheet(ss) {
  var sheet = ss.getSheetByName("📋 QUẢN LÝ BÁO GIÁ");
  sheet.setTabColor(THEME.NAVY);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "Thời gian gửi",
      "Mã báo giá",
      "Dòng sản phẩm",
      "Họ tên khách hàng",
      "Số điện thoại",
      "Nhắn Zalo",
      "Số lượng",
      "Quy cách / Chi tiết",
      "Phụ kiện chọn thêm",
      "Tổng tiền (VNĐ)",
      "Ghi chú khách hàng",
      "☑️ Đã Xong",
      "Trạng thái chi tiết"
    ]);
  }
  sheet.getRange("A1:M1").setFontWeight("bold").setBackground(THEME.NAVY).setFontColor(THEME.WHITE).setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(1, 38);
  sheet.setFrozenRows(1);

  sheet.setColumnWidth(1, 140);
  sheet.setColumnWidth(2, 130);
  sheet.setColumnWidth(3, 160);
  sheet.setColumnWidth(4, 170);
  sheet.setColumnWidth(5, 120);
  sheet.setColumnWidth(6, 110);
  sheet.setColumnWidth(7, 90);
  sheet.setColumnWidth(8, 180);
  sheet.setColumnWidth(9, 160);
  sheet.setColumnWidth(10, 140);
  sheet.setColumnWidth(11, 200);
  sheet.setColumnWidth(12, 100); // Checkbox Đã Xong
  sheet.setColumnWidth(13, 160); // Dropdown Trạng thái
}

function setupDemoSheet(ss) {
  var sheet = ss.getSheetByName("🎨 YÊU CẦU DEMO 2D");
  sheet.setTabColor("#0284c7");
  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "Thời gian gửi",
      "Mã yêu cầu",
      "Họ tên khách hàng",
      "Số điện thoại",
      "Nhắn Zalo",
      "Loại sản phẩm",
      "Số lượng dự kiến",
      "File Logo / Bản vẽ",
      "Ghi chú của khách",
      "☑️ Đã Gửi",
      "Trạng thái xử lý"
    ]);
  }
  sheet.getRange("A1:K1").setFontWeight("bold").setBackground("#0369a1").setFontColor(THEME.WHITE).setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(1, 38);
  sheet.setFrozenRows(1);

  sheet.setColumnWidth(1, 140);
  sheet.setColumnWidth(2, 120);
  sheet.setColumnWidth(3, 170);
  sheet.setColumnWidth(4, 120);
  sheet.setColumnWidth(5, 110);
  sheet.setColumnWidth(6, 160);
  sheet.setColumnWidth(7, 130);
  sheet.setColumnWidth(8, 180);
  sheet.setColumnWidth(9, 200);
  sheet.setColumnWidth(10, 100);
  sheet.setColumnWidth(11, 160);
}

function getFirstEmptyRow(sheet) {
  var values = sheet.getRange("A:A").getValues();
  for (var i = 1; i < values.length; i++) {
    if (!values[i][0] || values[i][0].toString().trim() === "") {
      return i + 1;
    }
  }
  return values.length + 1;
}

function sanitizeForSheet(val) {
  if (val === null || val === undefined) return "";
  var str = String(val);
  if (str.startsWith("=") || str.startsWith("+") || str.startsWith("-") || str.startsWith("@") || str.startsWith("\t") || str.startsWith("\r")) {
    return "'" + str;
  }
  return str;
}

function saveQuoteOrder(ss, data) {
  var sheet = ss.getSheetByName("📋 QUẢN LÝ BÁO GIÁ");
  if (!sheet) return;

  var accText = "Không";
  if (Array.isArray(data.accessories) && data.accessories.length > 0) {
    accText = data.accessories.join(", ");
  } else if (typeof data.accessories === "string" && data.accessories.trim() !== "") {
    accText = data.accessories;
  }

  var phone = String(data.phone || "").trim();
  var rawDigits = phone.replace(/[^0-9]/g, "");
  var zaloFormula = rawDigits ? '=HYPERLINK("https://zalo.me/' + rawDigits + '", "💬 Nhắn Zalo")' : "Không có";

  var specsText = String(data.specs || data.width || "");
  if (data.punched_hole && data.punched_hole !== "none") {
    var holeLabel = (data.punched_hole === "round") ? "Lỗ tròn" : "Lỗ con nhộng";
    if (specsText.indexOf("Lỗ") === -1) {
      specsText += " (Đục " + holeLabel + ")";
    }
  }

  var row = [
    data.created_at || new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }),
    sanitizeForSheet(data.id || data.quote_id || ("TL-" + Math.floor(1000 + Math.random() * 9000))),
    sanitizeForSheet(data.category || "Dây đeo thẻ"),
    sanitizeForSheet(data.customer_name || "Khách hàng"),
    "'" + phone,
    zaloFormula,
    data.quantity || 0,
    sanitizeForSheet(specsText),
    sanitizeForSheet(accText),
    data.total_price || 0,
    sanitizeForSheet(data.notes || ""),
    false, // Checkbox mặc định chưa xong
    "Mới"
  ];

  var targetRow = getFirstEmptyRow(sheet);
  sheet.getRange(targetRow, 1, 1, row.length).setValues([row]);
  sheet.setRowHeight(targetRow, 30);
  sheet.getRange(targetRow, 1, 1, 2).setHorizontalAlignment("center");
  sheet.getRange(targetRow, 5, 1, 3).setHorizontalAlignment("center");
  sheet.getRange(targetRow, 10).setNumberFormat("#,##0 \"đ\"").setFontWeight("bold").setFontColor("#b45309");

  // Gắn Checkbox vào cột L của dòng này
  sheet.getRange(targetRow, 12).insertCheckboxes();

  // Gắn Menu Dropdown vào cột M của dòng này
  applyDropdownToCell(sheet.getRange(targetRow, 13), ORDER_STATUSES);
}

function saveDemoRequest(ss, data) {
  var sheet = ss.getSheetByName("🎨 YÊU CẦU DEMO 2D");
  if (!sheet) return;

  var phone = String(data.phone || "").trim();
  var rawDigits = phone.replace(/[^0-9]/g, "");
  var zaloFormula = rawDigits ? '=HYPERLINK("https://zalo.me/' + rawDigits + '", "💬 Nhắn Zalo")' : "Không có";

  var row = [
    data.created_at || new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }),
    sanitizeForSheet(data.id || ("DM-" + Math.floor(1000 + Math.random() * 9000))),
    sanitizeForSheet(data.customer_name || "Khách hàng"),
    "'" + phone,
    zaloFormula,
    sanitizeForSheet(data.category || "Dây đeo thẻ"),
    sanitizeForSheet(data.quantity || "10-20"),
    sanitizeForSheet(data.specs || "Không đính kèm"),
    sanitizeForSheet(data.notes || ""),
    false, // Checkbox chưa gửi
    "Chờ gửi demo"
  ];

  var targetRow = getFirstEmptyRow(sheet);
  sheet.getRange(targetRow, 1, 1, row.length).setValues([row]);
  sheet.setRowHeight(targetRow, 30);
  sheet.getRange(targetRow, 1, 1, 2).setHorizontalAlignment("center");
  sheet.getRange(targetRow, 4, 1, 4).setHorizontalAlignment("center");

  sheet.getRange(targetRow, 10).insertCheckboxes();
  applyDropdownToCell(sheet.getRange(targetRow, 11), [
    "Chờ gửi demo", "Đã gửi demo", "Đang tư vấn", "Đã chốt", "Đã xong", "Đã hủy"
  ]);
}

function applyDropdownToCell(cellRange, options) {
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(options, true).setAllowInvalid(false).build();
  cellRange.setDataValidation(rule);
}

function setupStatusDropdownsAndColors() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var quotesSheet = ss.getSheetByName("📋 QUẢN LÝ BÁO GIÁ");
  if (!quotesSheet) return;

  var maxRows = quotesSheet.getMaxRows();

  // 1. Dọn dẹp sạch checkbox rỗng ở các dòng chưa có dữ liệu để không bị đẩy dữ liệu xuống dòng 1000
  if (maxRows >= 2) {
    quotesSheet.getRange("L2:L" + maxRows).removeCheckboxes();
    quotesSheet.getRange("L2:M" + maxRows).clearDataValidations();
  }

  // 2. Chỉ gắn Checkbox & Dropdown vào các dòng ĐÃ CÓ dữ liệu ở cột A
  var colA = quotesSheet.getRange("A2:A" + maxRows).getValues();
  for (var i = 0; i < colA.length; i++) {
    if (colA[i][0] && colA[i][0].toString().trim() !== "") {
      var rNum = i + 2;
      quotesSheet.getRange(rNum, 12).insertCheckboxes();
      applyDropdownToCell(quotesSheet.getRange(rNum, 13), ORDER_STATUSES);
    }
  }

  // 3. Tô màu tự động cho trạng thái (cột M)
  var statusRange = quotesSheet.getRange("M2:M" + maxRows);
  var rules = [];
  for (var j = 0; j < STATUS_COLORS.length; j++) {
    var r = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo(STATUS_COLORS[j].text)
      .setBackground(STATUS_COLORS[j].bg)
      .setFontColor(STATUS_COLORS[j].fg)
      .setBold(true)
      .setRanges([statusRange])
      .build();
    rules.push(r);
  }

  // 4. Nếu Checkbox = TRUE thì đổi màu xanh lá báo hiệu đã xử lý xong
  var doneRowRule = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied("=$L2=TRUE")
    .setBackground("#f0fdf4")
    .setFontColor("#15803d")
    .setRanges([quotesSheet.getRange("A2:M" + maxRows)])
    .build();
  rules.push(doneRowRule);

  quotesSheet.setConditionalFormatRules(rules);
}

function addSampleQuoteRow() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var mockData = {
    id: "TL-SAMPLE",
    customer_name: "Anh Tuấn (Công ty Tech)",
    phone: "0918889999",
    category: "Dây đeo thẻ Lụa Cao Cấp",
    quantity: 100,
    specs: "Bản 2.0cm, In nhiệt 2 mặt",
    accessories: ["Khóa móc kim loại", "Khóa an toàn"],
    total_price: 2850000,
    notes: "Đơn mẫu thử nghiệm hệ thống TagLuxe",
    created_at: new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })
  };
  saveQuoteOrder(ss, mockData);
  SpreadsheetApp.getUi().alert("✅ Đã thêm thành công 1 đơn hàng mẫu vào tab 'QUẢN LÝ BÁO GIÁ'! Mời bạn kiểm tra bảng tính và Dashboard.");
}

