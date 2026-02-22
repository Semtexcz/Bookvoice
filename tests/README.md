# Test Fixtures

- `tests/files/zero_to_one.pdf` is the canonical PDF fixture for Bookvoice tests.
- Use this file for smoke/integration scenarios that require a text-based PDF input.
- Unit tests live in `tests/unit/`.
- Integration tests live in `tests/integration/`.
- Run smoke coverage with standard tooling: `pytest tests/integration/test_smoke.py`.

# Provider Mock Strategy

- Keep provider tests deterministic and offline by mocking OpenAI adapters (`OpenAIChatClient`, `OpenAISpeechClient`) instead of real network calls.
- Prefer stage-level assertions that validate `PipelineStageError` stage/detail/hint mapping (`translate`, `rewrite`, `tts`).
- Use CLI integration tests to validate runtime source precedence (`CLI > secure storage > environment > defaults`) without requiring real API keys.
- Reuse small helper fixtures (for example deterministic in-memory WAV bytes and in-memory credential stores) to avoid global monkeypatch side effects.
