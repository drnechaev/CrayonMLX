"""Render contract. Adapters render through the application-owned model runtime."""

from pathlib import Path
from typing import Protocol

from crayonmlx.schemas import Preset


class RenderEngine(Protocol):
    id: str
    name: str
    base_models: tuple[str, ...]
    supports_strength: bool

    def available(self) -> bool: ...

    def render(self, preset: Preset, model: Path, source: Path, output: Path) -> dict | None: ...
