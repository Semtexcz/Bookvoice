"""Module entrypoint for running Bookvoice as ``python -m bookvoice``.

This module is also used by PyInstaller Windows builds to provide a stable
entry script for ``bookvoice.exe``.
"""

from __future__ import annotations

from bookvoice.cli import main


if __name__ == "__main__":
    main()
