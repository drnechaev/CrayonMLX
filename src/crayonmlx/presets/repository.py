"""Versionable JSON libraries with atomic replacement and safe identifiers."""

import re
from pathlib import Path
from threading import Lock
from uuid import NAMESPACE_URL, uuid4, uuid5

from crayonmlx.presets.defaults import initial_presets
from crayonmlx.presets.legacy_defaults import initial_presets as legacy_presets
from crayonmlx.schemas import Preset


class JsonRepository:
    def __init__(self, root: Path, directory: str, schema, defaults):
        self.root = root / directory
        self.schema = schema
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        marker = self.root / ".initialized"
        if not marker.exists():
            for item in defaults():
                self.save(uuid4().hex, item)
            marker.touch()

    def install_pack(self, name: str, items) -> None:
        """Add a built-in pack once, preserving edits and subsequent deletions."""
        marker = self.root / f".{name}"
        if marker.exists():
            return
        existing = {item["name"] for item in self.list()}
        for item in items:
            identifier = uuid5(NAMESPACE_URL, f"crayonmlx:{self.root.name}:{name}:{item.name}").hex
            if item.name not in existing and not self.path(identifier).exists():
                self.save(identifier, item)
                existing.add(item.name)
        marker.touch()

    def upgrade_pack(self, name: str, previous, replacement) -> None:
        """Replace only unchanged factory entries; never rewrite user content."""
        if (self.root / f".{name}").exists():
            return
        old = [self.schema.model_validate(item.model_dump()).model_dump() for item in previous]
        for entry in self.list():
            identifier = entry.pop("id")
            if entry in old:
                self.delete(identifier)
        self.install_pack(name, replacement)

    def path(self, identifier: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise ValueError("Некорректный идентификатор записи")
        return self.root / f"{identifier}.json"

    def list(self) -> list[dict]:
        with self.lock:
            return [
                {"id": path.stem, **self.schema.model_validate_json(path.read_text()).model_dump()}
                for path in sorted(self.root.glob("*.json"))
            ]

    def save(self, identifier: str, item) -> dict:
        with self.lock:
            path = self.path(identifier)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(item.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(path)
        return {"id": identifier, **item.model_dump()}

    def delete(self, identifier: str) -> None:
        with self.lock:
            self.path(identifier).unlink()


class PresetRepository(JsonRepository):
    def __init__(self, root: Path):
        super().__init__(root, "presets", Preset, initial_presets)
        self.upgrade_pack("drawing-builder-v2", legacy_presets(), initial_presets())
