# 3106 Lite (iOS)

Bản 3106 Lite được xây dựng từ mã nguồn mở [QuinnTang74/3106](https://github.com/QuinnTang74/3106) tại commit `8700bd458d284ca457f77e1f2eddf7fc8968d0eb` (3.2.5).

## Điều chỉnh

- **Tắt tính năng cập nhật** ở khởi động, khi quay lại từ nền và trang Cài đặt. Các hàm kiểm tra bản mới được thay bằng hàm không truy cập mạng.
- **Giao diện gọn**: 4 tab (Chức năng, Tệp, Dọn dẹp, Sao lưu).
- Trang chủ chỉ giữ: MobileGestalt, Quản lý tệp, Dọn dẹp, Sao lưu, Thay thế tệp, Ghi công, Cài đặt.
- Ẩn khỏi trang chủ: kho ứng dụng, nguồn tải, chuyển dữ liệu, hình nền, giao diện bàn phím, supervised và các tiện ích nâng cao. Mã nền của chúng được giữ để tránh hỏng phụ thuộc; chưa được xóa hoàn toàn khỏi binary.
- Đổi tên hiển thị thành **3106 Lite**. Bundle ID vẫn là `com.qingtang.3106`, nên bản Lite có thể thay thế app 3106 hiện tại khi ký bằng cùng bundle ID.
- Giữ nguyên kiểm tra hệ điều hành, xác nhận nguy hiểm và cơ chế bảo vệ dữ liệu.

## Build

GitHub → **Actions** → **Build 3106 Lite unsigned IPA** → **Run workflow**. Tải artifact **3106-Lite-unsigned-IPA** khi job thành công.

Bản `.ipa` được build **chưa ký**. Cần ký bằng chứng chỉ của chính bạn và giữ App Group entitlement phù hợp trên các phiên bản iOS cần nó. Không thể xác nhận chạy trên iPhone chỉ từ kết quả build.

## Giấy phép

GPL-3.0-or-later (giữ nguyên LICENSE/NOTICE của upstream trong checkout build). Phải tuân thủ nghĩa vụ cung cấp mã nguồn tương ứng khi phân phối phiên bản sửa đổi. Nguồn gốc: [QuinnTang74/3106](https://github.com/QuinnTang74/3106).
