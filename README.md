# Project Exam: CI/CD Pipeline with Docker & SonarQube for a FastAPI Application

This project implements a complete CI/CD pipeline that containerizes a FastAPI application, runs automated tests, enforces code quality with SonarQube quality gates, and deploys using a Blue-Green zero-downtime strategy.

## Questions & Answers

### 1. Explain why multi-stage builds are used in the Dockerfile and how they improve both image size and security.
**Answer:**
Multi-stage builds are used to separate the build environment from the runtime environment in a Docker image. 
- **Image Size Improvement:** By using a `builder` stage, we can install dependencies (like `gcc`, build tools, and `pip` packages) to compile and prepare the application environment. In the `runtime` stage, we only copy the necessary artifacts (like the compiled python virtual environment) from the builder stage. This drastically reduces the final image size by discarding build tools and cache files.
- **Security Improvement:** A smaller image means a smaller attack surface. Because the final runtime image doesn't contain build tools, compilers, or package managers (which could be exploited by attackers to download or compile malicious payloads), the container is much more secure. Furthermore, our Dockerfile implements a non-root user (`appuser`) in the runtime stage, ensuring that even if the container is compromised, the attacker does not have root privileges.

### 2. Describe the complete CI/CD pipeline flow from a developer pushing code to the application being deployed in production.
**Answer:**
The CI/CD pipeline is designed as an automated workflow using GitHub Actions that triggers when a developer pushes code to the `main` branch or creates a pull request:
1. **Lint Stage:** Checks the codebase using `black` and `ruff` to ensure compliance with styling guidelines and syntactical correctness.
2. **Test & Coverage Stage:** Runs unit tests using `pytest` and generates a code coverage report (`coverage.xml`), which is then uploaded as an artifact for the next stages.
3. **SonarQube Scan & Quality Gate Stage:** Downloads the coverage report and runs a static code analysis using SonarQube. It checks the code against a predefined Quality Gate. If the code contains bugs, vulnerabilities, or lacks test coverage (violating the Quality Gate), the pipeline execution is **blocked** and fails here.
4. **Build Stage:** Containerizes the application by building the multi-stage Dockerfile to ensure it builds correctly. It leverages Docker build caching for faster executions.
5. **Deploy Stage (Blue-Green):** Once all previous stages (especially the Quality Gate) pass, the deploy job triggers. It executes a deployment script (`deploy.sh`) that spins up the new version (e.g., Green) alongside the active version (Blue). It runs health checks on the new container, and only routes traffic to it once it is marked as `healthy`, subsequently shutting down the old container. If the new version fails the health check, a rollback is performed by keeping the active container.

### 3. How does the SonarQube quality gate integrate with the pipeline, and what happens when the gate fails?
**Answer:**
The SonarQube quality gate integrates with the pipeline through the `sonarqube-quality-gate-action` in GitHub Actions.
- In the **SonarQube Scan** step, the code and the `coverage.xml` generated during the test stage are analyzed, and the results are pushed to the SonarQube server.
- The **Quality Gate check** step polls the SonarQube server to retrieve the status of the Quality Gate assigned to the project.
- **When the gate fails:** The GitHub Actions step receives a failure status from SonarQube. This causes the pipeline to immediately halt, failing the `sonarqube` job. Because the subsequent jobs (`build` and `deploy`) depend on the success of the `sonarqube` job (using `needs: sonarqube`), they are completely blocked from running. This ensures that substandard or insecure code is never deployed to the production environment.

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
- **SonarQube Server**: Bạn cần có một server SonarQube đang hoạt động (Local qua Docker kết hợp Ngrok, hoặc dùng SonarCloud).
- Vào kho lưu trữ GitHub của bạn -> **Settings** -> **Secrets and variables** -> **Actions**.
- Thêm 2 repository secrets bắt buộc:
  - `SONAR_HOST_URL`: URL public của SonarQube.
  - `SONAR_TOKEN`: Token được tạo từ project trên SonarQube.

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
1. **Lint Code**: Kiểm tra định dạng code và lỗi bằng `uv pip install ruff black`.
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
