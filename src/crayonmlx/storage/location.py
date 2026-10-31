"""Copy internal data to a new location, preserving model/image paths and the source."""

import json
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

from crayonmlx.paths import location_file

INTERNAL_FOLDERS = ("presets", "prompt-templates", "generation-configs")


def prepare_location(state, destination: str) -> Path:
    target = Path(destination).expanduser()
    if not target.is_absolute():
        raise ValueError("Укажите абсолютный путь к внутренним данным")
    target = target.resolve()
    source = state.root.resolve()
    if target == source:
        return target
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("Новая папка не должна содержать текущую папку данных или находиться внутри неё")
    settings = state.database.settings()
    for existing in (Path(settings.models_dir), Path(settings.output_dir)):
        if target == existing or target.is_relative_to(existing) or existing.is_relative_to(target):
            raise ValueError("Выберите отдельную папку для внутренних данных, без моделей и результатов")
    if state.database.has_active_jobs() or any(
        item["status"] in ("queued", "running") for item in state.downloads.list()
    ):
        raise ValueError("Дождитесь завершения генераций и скачиваний")
    if state.runtime.snapshot()["phase"] in {"starting", "loading", "preparing", "denoising", "decoding"}:
        raise ValueError("Дождитесь завершения операции с моделью")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("Для переноса выберите пустую папку. Существующие данные не перезаписываются.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".crayonmlx-transfer-{uuid4().hex}"
    temporary.mkdir()
    published = False
    try:
        with state.database.connect() as original, sqlite3.connect(temporary / "crayonmlx.sqlite3") as backup:
            original.backup(backup)
        for folder in INTERNAL_FOLDERS:
            if (source / folder).exists():
                shutil.copytree(source / folder, temporary / folder)
        if state.tokens.path.exists():
            shutil.copy2(state.tokens.path, temporary / "hf-token")
            (temporary / "hf-token").chmod(0o600)
        if target.exists():
            target.rmdir()  # Only succeeds if it is still empty.
        temporary.replace(target)
        published = True
        locator = location_file()
        locator.parent.mkdir(parents=True, exist_ok=True)
        pending = locator.with_name(f".{locator.name}-{uuid4().hex}")
        try:
            pending.write_text(json.dumps({"data_dir": str(target)}), encoding="utf-8")
            pending.replace(locator)
        finally:
            pending.unlink(missing_ok=True)
        return target
    except Exception:
        # Remove only this operation's new copy; never remove or modify the source.
        if published:
            shutil.rmtree(target)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
