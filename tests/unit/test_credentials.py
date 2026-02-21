"""Unit tests for secure credential store helpers."""

from bookvoice.credentials import KeyringCredentialStore


class FakeKeyringModule:
    """In-memory keyring stub for deterministic credential store tests."""

    def __init__(self) -> None:
        """Initialize fake storage dictionary."""

        self._storage: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, account_name: str) -> str | None:
        """Return previously stored password if present."""

        return self._storage.get((service_name, account_name))

    def set_password(self, service_name: str, account_name: str, value: str) -> None:
        """Store password value for the service/account key."""

        self._storage[(service_name, account_name)] = value

    def delete_password(self, service_name: str, account_name: str) -> None:
        """Delete password value for the service/account key."""

        self._storage.pop((service_name, account_name), None)


def test_keyring_store_roundtrip_set_get_clear(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Keyring store should set/get/clear API key values via keyring backend."""

    fake_keyring = FakeKeyringModule()
    store = KeyringCredentialStore()
    monkeypatch.setattr(store, "_load_keyring_module", lambda: fake_keyring)

    assert store.is_available() is True
    assert store.get_api_key() is None

    store.set_api_key("  abc123  ")
    assert store.get_api_key() == "abc123"

    assert store.clear_api_key() is True
    assert store.get_api_key() is None
    assert store.clear_api_key() is False


def test_keyring_store_handles_missing_keyring_module() -> None:
    """Keyring store should degrade safely when keyring package is unavailable."""

    store = KeyringCredentialStore()
    store._load_keyring_module = lambda: None  # type: ignore[method-assign]

    assert store.is_available() is False
    assert store.get_api_key() is None
    assert store.clear_api_key() is False
