"""Local HF credential, never returned by the settings endpoint or put in jobs."""

import os
from pathlib import Path


class TokenStore:
    def __init__(self, root: Path):
        self.path = root / "hf-token"

    def get(self) -> str | None:
        return self.path.read_text(encoding="utf-8").strip() if self.path.exists() else None

    def set(self, token: str) -> None:
        if not token:
            self.path.unlink(missing_ok=True)
            return
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(token)
        self.path.chmod(0o600)
