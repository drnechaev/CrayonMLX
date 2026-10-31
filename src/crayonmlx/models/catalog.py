"""Discover manually downloaded Diffusers or MFLUX checkpoint directories."""

from pathlib import Path

from crayonmlx.models.identity import model_description
from crayonmlx.paths import child_path

MARKERS = ("model_index.json", "config.json", "transformer", "vae", "text_encoder", "mflux_model.json")


def is_checkpoint(path: Path) -> bool:
    return path.is_dir() and any((path / marker).exists() for marker in MARKERS)


def list_models(root: Path) -> list[dict]:
    if not root.is_dir():
        return []
    # A directory may itself be a checkpoint, or contain named checkpoints.
    paths = [root] if is_checkpoint(root) else sorted(root.iterdir())
    return [
        {
            "id": "." if path == root else path.name,
            "name": path.name,
            "path": str(path),
            **model_description(path),
        }
        for path in paths
        if not path.name.startswith(".")
        and is_checkpoint(path)
        and path.resolve().is_relative_to(root.resolve())
    ]


def resolve_model(root: Path, identifier: str) -> Path:
    path = root.resolve() if identifier == "." else child_path(root, identifier)
    if not is_checkpoint(path):
        raise ValueError(
            "Не найдена локальная папка модели. Нужен полный checkpoint, а не отдельный файл весов."
        )
    return path
