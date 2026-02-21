# Test Fixtures

- `tests/files/zero_to_one.pdf` is the canonical PDF fixture for Bookvoice tests.
- Use this file for smoke/integration scenarios that require a text-based PDF input.
- Unit tests live in `tests/unit/`.
- Integration tests live in `tests/integration/`.
- Run smoke coverage with standard tooling: `pytest tests/integration/test_smoke.py`.
