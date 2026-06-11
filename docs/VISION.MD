# Bookvoice Vision

## Purpose

Bookvoice converts text-based `.pdf` and `.epub` books into deterministic
Czech audiobook outputs with reproducible intermediate artifacts.

## Users

- Developers and technical users who want a scriptable audiobook conversion
  pipeline.
- Power users who need resumable, auditable processing for long source books.
- Maintainers who need deterministic fixtures and fast regression tests.

## Value

Bookvoice should make long-running document-to-audio workflows predictable:

- source extraction is inspectable
- chapter and chunk boundaries are deterministic
- provider calls can be resumed or replayed from artifacts
- packaged audio outputs are named and tagged consistently
- command output is safe for CI logs and troubleshooting

## Non-Goals

- Bookvoice is not a DRM bypass tool.
- Bookvoice is not intended for copyrighted material without proper rights.
- Bookvoice does not aim to hide provider costs or network dependencies.
- Bookvoice should not depend on live provider calls for fast unit tests.

## Product Direction

The project should favor a reliable CLI-first pipeline before broadening into
packaging, API, or UI surfaces. New capabilities should preserve deterministic
artifacts, clear error surfaces, and documented recovery paths.
