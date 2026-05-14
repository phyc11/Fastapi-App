# Hướng dẫn chi tiết thiết lập SonarQube cho dự án

Để chạy SonarQube và tích hợp nó vào quá trình CI/CD với GitHub Actions, bạn cần thực hiện tuần tự các bước sau đây. Do GitHub Actions chạy trên server của GitHub, nó không thể gọi trực tiếp `localhost:9000` trên máy tính của bạn. Vì vậy chúng ta phải dùng `ngrok` để tạo một đường hầm (tunnel) public.

## Bước 1: Khởi chạy SonarQube qua Docker
Mở terminal (PowerShell hoặc CMD) và chạy câu lệnh sau để tải và chạy SonarQube:
```bash
docker run -d --name sonarqube -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true -p 9000:9000 sonarqube:latest
```
- Truy cập vào giao diện web SonarQube: **http://localhost:9000**
- Đăng nhập với tài khoản mặc định: 
  - Username: `admin`
  - Password: `admin`
*(Hệ thống sẽ yêu cầu bạn đổi mật khẩu mới ở lần đăng nhập đầu tiên).*

## Bước 2: Tạo Public URL bằng Ngrok
Mở một terminal mới và chạy ngrok (đảm bảo ngrok đã được cài đặt, nếu chưa thì tải tại ngrok.com):
```bash
ngrok http 9000
```
- Màn hình terminal sẽ hiện ra dòng `Forwarding: https://<random-id>.ngrok-free.app -> http://localhost:9000`
- Sao chép cái URL `https://<random-id>.ngrok-free.app` này lại. Đây chính là `SONAR_HOST_URL` của bạn.

## Bước 3: Tạo Project và lấy Token trên SonarQube
1. Tại giao diện web SonarQube (qua localhost hoặc link ngrok), nhấn **Create Project** -> **Manually**.
2. Nhập `Project key` và `Display name`. Chú ý: `Project key` phải khớp với giá trị `sonar.projectKey` trong file `sonar-project.properties` của code (hiện tại là `my-fastapi-app`).
3. Set up project: Chọn **Locally** thay vì GitHub.
4. Chọn **Generate a token**:
   - Đặt tên cho token (vd: `github-actions-token`).
   - Nhấn **Generate** và copy chuỗi mã token đó lại. Đây chính là giá trị `SONAR_TOKEN`. Cất cẩn thận vì bạn sẽ không thể xem lại mã này sau khi đóng hộp thoại.
5. Chọn loại dự án (Python) và kết thúc quá trình setup.

## Bước 4: Thiết lập Quality Gate (Cổng chất lượng)
Để pipeline bị chặn lại nếu code dở, bạn phải bắt buộc có Quality Gate.
1. Trên menu trên cùng của SonarQube, chọn **Quality Gates**.
2. Nhấn **Create** để tạo một Quality Gate mới (vd: `FastAPI-Gate`).
3. Add Condition (Thêm điều kiện fail), ví dụ: 
   - `Coverage on New Code` < 80%
   - Hoặc `Bugs` > 0
   - Hoặc `Security Hotspots Reviewed` < 100%
4. Lưu lại, ở góc bên trái, chọn Project của bạn `My FastAPI App` và **Assign** nó cho Quality Gate bạn vừa tạo.

## Bước 5: Cấu hình GitHub Secrets
1. Vào Repo code của bạn trên GitHub.
2. Chọn **Settings** -> Nhìn thanh menu bên trái chọn **Secrets and variables** -> **Actions**.
3. Nhấn **New repository secret**:
   - `Name`: `SONAR_HOST_URL`
   - `Secret`: Dán cái link ngrok public vào (vd: `https://abcd.ngrok-free.app`)
4. Nhấn **Add secret**
5. Lặp lại để thêm Secret thứ 2:
   - `Name`: `SONAR_TOKEN`
   - `Secret`: Dán cái chuỗi token ở Bước 3 vào.

Xong! Bây giờ khi bạn `git push` code lên, GitHub Actions sẽ tự động đọc `SONAR_TOKEN` và đẩy kết quả phân tích sang server SonarQube của bạn thông qua URL `SONAR_HOST_URL`. Nếu Code Coverage hoặc Bugs vi phạm Quality Gate ở Bước 4, luồng Pipeline lập tức sẽ thất bại (Red/Failed) và ngăn cản quá trình Deploy.

sqp_85f006d5217b08bfc75dbee1ab68361aaba98295


