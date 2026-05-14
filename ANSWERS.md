# Answers to Final Exam Questions

### 1. Explain why multi-stage builds are used in the Dockerfile and how they improve both image size and security.
**Answer:**
Multi-stage builds are used to separate the build environment from the runtime environment in a Docker image. 
- **Image Size Improvement:** By using a `builder` stage, we can install dependencies to compile and prepare the application environment. In the `runtime` stage, we only copy the necessary artifacts from the builder stage. This reduces the final image size by discarding build tools and cache files.
- **Security Improvement:** A smaller image means a smaller attack surface. Because the final runtime image doesn't contain build tools, compilers, or package managers which could be exploited by attackers to download or compile malicious payloads, the container is more secure. Furthermore, our Dockerfile implements a non-root user (`appuser`) in the runtime stage, ensuring that even if the container is compromised, the attacker does not have root privileges.

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
