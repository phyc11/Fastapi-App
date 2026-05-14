# Project Exam: CI/CD Pipeline with Docker & SonarQube for a FastAPI Application

This project implements a complete CI/CD pipeline that containerizes a FastAPI application, runs automated tests, enforces code quality with SonarQube quality gates, and deploys using a Blue-Green zero-downtime strategy.



## Project Structure
- `Dockerfile`: Multi-stage Dockerfile for FastAPI.
- `.dockerignore`: Exclusions for the Docker context.
- `docker-compose.yml`: Configuration for running the app in a Blue-Green deployment architecture.
- `deploy.sh`: Deployment script to handle the Blue-Green environment switch and health checks.
- `.github/workflows/ci-cd.yml`: GitHub Actions pipeline definition.
- `sonar-project.properties`: Configuration for SonarQube analysis and test coverage paths.
- `src/`: The FastAPI application code.
- `tests/`: Unit tests utilizing pytest.

## Hướng dẫn chạy và kiểm thử Full CI/CD Pipeline

Dưới đây là các bước để chạy toàn bộ quy trình CI/CD và xác minh các yêu cầu của bài tập:

### 1. Chuẩn bị môi trường SonarQube & GitHub Secrets

**A. Khởi chạy SonarQube qua Docker Local:**
Mở terminal và chạy lệnh sau để khởi chạy SonarQube server:
```bash
docker run -d --name sonarqube -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true -p 9000:9000 sonarqube:latest
```
Truy cập `http://localhost:9000` (User/Pass mặc định: `admin`/`admin`). Tạo project mới (chọn Locally) với Project key là `my-fastapi-app` và tạo một Token.

**B. Mở cổng mạng bằng Ngrok:**
Vì GitHub Actions chạy trên đám mây, nó cần URL public để gửi report về máy bạn. Mở một terminal khác và chạy:
```powershell
.\ngrok.exe http 9000
```
*(Copy đường dẫn `https://xxxx.ngrok-free.app` được sinh ra)*

**C. Cấu hình GitHub Secrets:**
- Vào kho lưu trữ GitHub của bạn -> **Settings** -> **Secrets and variables** -> **Actions**.
- Thêm 2 repository secrets bắt buộc:
  - `SONAR_HOST_URL`: Đường dẫn public lấy từ terminal ngrok ở bước trên.
  - `SONAR_TOKEN`: Mã Token bảo mật bạn vừa tạo từ SonarQube Dashboard.

### 2. Kích hoạt GitHub Actions (CI/CD)
Pipeline đã được thiết kế sẵn trong `.github/workflows/ci-cd.yml` và sẽ tự động kích hoạt khi bạn đẩy code lên GitHub.
```bash
git init
git add .
git commit -m "Project Exam CI/CD Setup"
git branch -M main
git remote add origin <URL_GITHUB_REPO_CỦA_BẠN>
git push -u origin main
```

Mở tab **Actions** trên GitHub repository để xem tiến trình chạy của các Jobs:
1. **Lint Code**: Kiểm tra định dạng code và lỗi.
2. **Run Tests and Coverage**: Chạy Unit tests bằng lệnh `pytest --cov=src --cov-report=xml` (sẽ sinh ra file `coverage.xml`).
3. **SonarQube Scan & Quality Gate**: Phân tích mã nguồn dựa trên code và `coverage.xml`. Nếu không đạt chuẩn Quality Gate (vd: Coverage < 80%, có Vulnerabilities), **pipeline sẽ thất bại (blocked) và dừng lại**, ngăn không cho chạy bước tiếp theo.
4. **Build Docker Image**: Tiến hành build multi-stage image. Image được thu nhỏ và bảo mật qua User `appuser`.
5. **Deploy (Blue-Green)**: Khởi chạy kịch bản Blue-Green qua mô phỏng của `deploy.sh`.

### 3. Chạy và kiểm thử Blue-Green Deploy trên Local
Để mô phỏng chính xác những gì Deploy Job thực hiện, bạn có thể chạy file Bash script trực tiếp trên máy của mình (yêu cầu Docker Desktop & Git Bash / WSL / Linux):
```bash
bash deploy.sh
```
- **Lần chạy đầu tiên**: Script nhận diện chưa có container, khởi tạo môi trường **blue** (port `8001`), đợi health check `healthy`.
- **Lần chạy thứ hai**: Script nhận diện **blue** đang chạy, tiến hành khởi tạo môi trường **green** (port `8002`). Nếu **green** pass health check, traffic được mô phỏng chuyển đổi sang green và script sẽ stop container **blue**.
- **Rollback tự động**: Nếu bản release mới (vd green) bị lỗi (crash, sai port) dẫn đến health check thất bại, script sẽ in ra log lỗi, dừng ngay quá trình deploy và giữ nguyên bản **blue** đang ổn định, đạt yêu cầu *Zero-Downtime*.
