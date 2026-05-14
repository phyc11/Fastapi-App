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
3. **SonarQube Scan & Quality Gate**: Phân tích mã nguồn dựa trên code và `coverage.xml`. Nếu không đạt chuẩn Quality Gate (vd: Coverage < 80%, có Vulnerabilities), **pipeline sẽ thất bại (blocked) và dừng lại**.
4. **Build, Push & Scan (Trivy)**: Build Docker image từ Dockerfile, sau đó **đẩy thẳng lên kho lưu trữ GitHub Container Registry (GHCR)**. Tiếp theo, sử dụng công cụ **Trivy** để quét các lỗ hổng bảo mật bên trong Image.
5. **Deploy (Blue-Green)**: Kích hoạt Self-hosted Runner trên máy chủ của bạn để kéo (pull) Image từ GHCR về và tự động chạy kịch bản `deploy.sh`.

### 3. Hướng dẫn thiết lập Self-hosted Runner để Deploy Thực tế
Dự án này sử dụng mô hình Deploy chuẩn Enterprise: Máy chủ (VPS/Local) sẽ lắng nghe lệnh từ GitHub Actions thông qua Self-hosted Runner.
1. Vào Repo GitHub -> **Settings** -> **Actions** -> **Runners** -> **New self-hosted runner**.
2. Làm theo hướng dẫn trên màn hình để tải và cài đặt Runner trên máy của bạn (Windows/Linux).
3. Chạy file `run.cmd` (hoặc `./run.sh`). Màn hình hiển thị `Listening for Jobs` nghĩa là đã sẵn sàng.
4. Mỗi khi có code mới được merge vào nhánh `main`, GitHub Actions sẽ chạy qua các bước kiểm định (SonarQube, Trivy). Nếu tất cả đều **Passed**, nó sẽ ra lệnh cho con Runner trên máy bạn tự động gọi file `bash deploy.sh`.

- **Lần chạy đầu tiên**: Script nhận diện chưa có container, tải Image từ GHCR, khởi tạo môi trường **blue** (port `8001`), đợi health check `healthy`.
- **Lần chạy thứ hai**: Script nhận diện **blue** đang chạy, khởi tạo môi trường **green** (port `8002`). Nếu **green** pass health check, traffic được chuyển sang green và script sẽ stop container **blue**.
- **Rollback tự động**: Nếu bản release mới bị lỗi dẫn đến health check thất bại, script sẽ in ra log lỗi, dừng quá trình deploy và giữ nguyên bản đang ổn định, đạt yêu cầu *Zero-Downtime*.
