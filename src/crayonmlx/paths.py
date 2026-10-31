"""Application-owned data lives separately from user-selected model/output folders."""

import json
import os
from pathlib import Path

from platformdirs import user_config_path, user_data_path


def location_file() -> Path:
    return user_config_path("crayonmlx", appauthor=False) / "location.json"


def data_directory() -> Path:
    locator = location_file()
    if locator.exists():
        value = json.loads(locator.read_text(encoding="utf-8"))["data_dir"]
        path = Path(value).expanduser()
        if not path.is_absolute() or not (path / "crayonmlx.sqlite3").is_file():
            raise ValueError("Сохранённая папка данных недоступна. Проверьте location.json.")
        return path.resolve()
    return (
        Path(os.environ.get("CRAYONMLX_DATA_DIR", user_data_path("crayonmlx", appauthor=False)))
        .expanduser()
        .resolve()
    )


def child_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError("Путь должен находиться внутри папки моделей")
    return path
