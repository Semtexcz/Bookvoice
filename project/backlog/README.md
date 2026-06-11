# Backlog Priority Index

This index lists active backlog tasks by priority. Dependencies are the task
cards, completed tasks, or project files that should be available before each
task is implemented.

## P1

| Task | Title | Dependencies |
| --- | --- | --- |
| [TASK-015](2026-02-21-task-015-online-model-pricing-for-cost-tracker.md) | Fetch model pricing online for run cost calculation | TASK-011, TASK-014 |
| [TASK-057](2026-02-25-task-057-windows-code-signing-and-smartscreen-reputation.md) | Add Windows code-signing pipeline and SmartScreen mitigation | TASK-054, TASK-055, `.github/workflows/windows-release.yml` |
| [TASK-058](2026-02-28-linux-deb-packaging/2026-02-28-task-058-linux-deb-target-and-install-layout.md) | Define Linux Debian package target, support policy, and install layout | `pyproject.toml`, `README.md` |
| [TASK-059](2026-02-28-linux-deb-packaging/2026-02-28-task-059-linux-deb-build-and-dependencies.md) | Build a Debian package for Bookvoice and define dependency handling | TASK-058, `pyproject.toml`, `README.md` |
| [TASK-069](2026-03-15-reader-graphics-preservation/2026-03-15-task-069-reader-export-image-preservation-contract.md) | Define image-preservation contract for reader-only translation exports | TASK-062, TASK-064, TASK-065 |
| [TASK-070](2026-03-15-reader-graphics-preservation/2026-03-15-task-070-source-image-extraction-and-placement-artifact.md) | Add source image extraction and placement artifact for reader exports | TASK-063, TASK-067, TASK-069 |
| [TASK-071](2026-03-15-reader-graphics-preservation/2026-03-15-task-071-preserve-images-in-translated-epub-export.md) | Preserve source images in translated EPUB export | TASK-064, TASK-069, TASK-070 |
| [TASK-072](2026-03-15-reader-graphics-preservation/2026-03-15-task-072-preserve-images-in-translated-pdf-export.md) | Preserve source images in translated PDF export | TASK-065, TASK-069, TASK-070 |
| [TASK-073](2026-05-15-fastapi-rest-api/2026-05-15-task-073-fastapi-application-foundation.md) | Add FastAPI application foundation | TASK-014, TASK-036, TASK-040 |
| [TASK-074](2026-05-15-fastapi-rest-api/2026-05-15-task-074-api-request-response-contracts.md) | Define REST API request and response contracts | TASK-073, TASK-024, TASK-043, TASK-066 |
| [TASK-075](2026-05-15-fastapi-rest-api/2026-05-15-task-075-api-job-orchestration-and-status.md) | Add API job orchestration and status tracking | TASK-073, TASK-074, TASK-019, TASK-037 |
| [TASK-076](2026-05-15-fastapi-rest-api/2026-05-15-task-076-api-source-upload-and-artifact-access.md) | Add source upload and artifact access endpoints | TASK-073, TASK-074, TASK-075, TASK-066, TASK-068 |
| [TASK-078](2026-05-15-fastapi-rest-api/2026-05-15-task-078-api-configuration-and-security.md) | Add API configuration and baseline security controls | TASK-014, TASK-036, TASK-040, TASK-073 |
| [TASK-080](2026-06-10-task-080-llm-processing-activity-feedback.md) | Add activity feedback during long LLM processing stages | TASK-019 |
| [TASK-082](2026-06-10-task-082-resume-interrupted-build-before-final-manifest.md) | Support resume for interrupted builds before final manifest write | TASK-008, TASK-037, TASK-080 |
| [TASK-083](2026-06-11-task-083-bounded-concurrent-provider-processing.md) | Add bounded concurrent provider processing for long books | TASK-012, TASK-019, TASK-080, TASK-082 |

## P2

| Task | Title | Dependencies |
| --- | --- | --- |
| [TASK-044](2026-02-22-task-044-language-proficiency-level-control-for-learning-output.md) | Language proficiency level control for learning-friendly output | TASK-014, TASK-034, TASK-040, TASK-043 |
| [TASK-060](2026-02-28-linux-deb-packaging/2026-02-28-task-060-linux-deb-release-automation.md) | Add CI and release automation for Linux Debian package artifacts | TASK-058, TASK-059, `.github/workflows` |
| [TASK-061](2026-02-28-linux-deb-packaging/2026-02-28-task-061-linux-deb-user-installation-docs.md) | Document Linux Debian package installation, upgrades, and troubleshooting | TASK-058, TASK-059, TASK-060, `README.md` |
| [TASK-077](2026-05-15-fastapi-rest-api/2026-05-15-task-077-api-chapter-discovery-endpoints.md) | Add chapter discovery endpoints | TASK-016, TASK-017, TASK-066, TASK-067, TASK-068, TASK-076 |
| [TASK-079](2026-05-15-fastapi-rest-api/2026-05-15-task-079-api-docs-and-deployment-packaging.md) | Document and package the REST API server | TASK-073, TASK-075, TASK-076, TASK-078 |
| [TASK-081](2026-06-10-task-081-show-time-in-log-output.md) | Show time in log output | TASK-019, TASK-080 |

## Notes

- Priority order is taken from each task card's `Priority` field.
- Dependency entries are taken from each task card's `Related` field and kept
  explicit here for planning.
- Completed dependency tasks live under `project/done/`.
