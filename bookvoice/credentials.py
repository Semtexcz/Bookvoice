"""Secure credential storage helpers for Bookvoice CLI.

Responsibilities:
- Persist provider API keys in an OS-backed secure credential store.
- Provide deterministic read/write/delete operations for provider credentials.
- Avoid logging or exposing secret values in diagnostics.

Key types:
- `CredentialStore`: interface for provider credential persistence.
- `KeyringCredentialStore`: keyring-backed secure credential storage.
"""

from __future__ import annotations

from dataclasses import dataclass


_DEFAULT_SERVICE_NAME = "bookvoice"
_DEFAULT_ACCOUNT_NAME = "openai_api_key"


class CredentialStore:
    """Interface for secure provider credential operations."""

    def is_available(self) -> bool:
        """Return whether secure credential operations are available."""

        raise NotImplementedError

    def get_api_key(self) -> str | None:
        """Load the stored API key from secure storage, when available."""

        raise NotImplementedError

    def set_api_key(self, api_key: str) -> None:
        """Persist an API key in secure storage."""

        raise NotImplementedError

    def clear_api_key(self) -> bool:
        """Delete a stored API key and return whether one existed."""

        raise NotImplementedError


@dataclass(slots=True)
class KeyringCredentialStore(CredentialStore):
    """Secure credential store backed by the `keyring` package."""

    service_name: str = _DEFAULT_SERVICE_NAME
    account_name: str = _DEFAULT_ACCOUNT_NAME

    def _load_keyring_module(self):
        """Import and return the optional `keyring` module when installed."""

        try:
            import keyring  # type: ignore
        except ImportError:
            return None
        return keyring

    def is_available(self) -> bool:
        """Return `True` when `keyring` can be imported in this environment."""

        return self._load_keyring_module() is not None

    def get_api_key(self) -> str | None:
        """Get a normalized API key from keyring, returning `None` when missing."""

        keyring_module = self._load_keyring_module()
        if keyring_module is None:
            return None
        value = keyring_module.get_password(self.service_name, self.account_name)
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    def set_api_key(self, api_key: str) -> None:
        """Persist a normalized API key in keyring or raise when unavailable."""

        keyring_module = self._load_keyring_module()
        if keyring_module is None:
            raise RuntimeError(
                "Secure credential storage is unavailable because `keyring` is not "
                "installed. Install `keyring` to persist API keys securely."
            )

        normalized = api_key.strip()
        if not normalized:
            raise ValueError("API key must be a non-empty string.")
        keyring_module.set_password(self.service_name, self.account_name, normalized)

    def clear_api_key(self) -> bool:
        """Remove the stored API key from keyring and report if one was present."""

        keyring_module = self._load_keyring_module()
        if keyring_module is None:
            return False

        existing = self.get_api_key()
        if existing is None:
            return False

        keyring_module.delete_password(self.service_name, self.account_name)
        return True


def create_credential_store() -> CredentialStore:
    """Create the default secure credential store implementation."""

    return KeyringCredentialStore()
