"""Identify supported checkpoints without importing MLX or reading tensor weights."""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelIdentity:
    engine: str
    base_model: str
    label: str


VARIANTS = {
    "qwen-image-edit": ModelIdentity("mflux-qwen-edit", "qwen-image-edit", "Qwen Image Edit 2509"),
    "qwen-image-edit-2511": ModelIdentity("mflux-qwen-edit", "qwen-image-edit-2511", "Qwen Image Edit 2511"),
    "dev": ModelIdentity("mflux-flux", "dev", "FLUX.1 Dev"),
    "schnell": ModelIdentity("mflux-flux", "schnell", "FLUX.1 Schnell"),
    "krea-dev": ModelIdentity("mflux-flux", "krea-dev", "FLUX.1 Krea Dev"),
}
PIPELINES = {"FluxPipeline": "mflux-flux", "QwenImageEditPlusPipeline": "mflux-qwen-edit"}
TRANSFORMERS = {"FluxTransformer2DModel": "mflux-flux", "QwenImageTransformer2DModel": "mflux-qwen-edit"}


def read_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise ValueError(f"Не удалось прочитать конфигурацию {path.name}") from None
    if not isinstance(value, dict):
        raise ValueError(f"Некорректная конфигурация {path.name}")
    return value


def named_variant(value: str, *, aliases: bool = False) -> str | None:
    name = value.lower().replace("--", "/").replace("_", "-").rstrip("/").rsplit("/", 1)[-1]
    if aliases and name in VARIANTS:
        return name
    patterns = {
        "qwen-image-edit-2511": r"qwen-image-edit-2511",
        "qwen-image-edit": r"qwen-image-edit-2509",
        "krea-dev": r"flux\.1-krea-dev",
        "schnell": r"flux\.1-schnell",
        "dev": r"flux\.1-dev",
    }
    for variant, pattern in patterns.items():
        if re.fullmatch(pattern + r"(?:-(?:[34568]bit|quantized|mlx))*", name):
            return variant
    return None


def identify_model(path: Path) -> ModelIdentity:
    manifest = read_config(path / "mflux_model.json")
    index = read_config(path / "model_index.json")
    transformer = read_config(path / "transformer" / "config.json")
    root_config = read_config(path / "config.json")
    upstream = manifest.get("upstream") or {}
    if not isinstance(upstream, dict):
        raise ValueError("Некорректные метаданные источника модели")
    explicit = set()
    for value in (
        manifest.get("base_model"),
        manifest.get("model_name"),
        upstream.get("repo_id"),
        index.get("_name_or_path"),
        root_config.get("_name_or_path"),
    ):
        if isinstance(value, str) and (variant := named_variant(value, aliases=True)):
            explicit.add(variant)
    base_model = manifest.get("base_model")
    if base_model and (not isinstance(base_model, str) or base_model not in VARIANTS):
        raise ValueError("Этот вариант модели пока не поддерживается")
    # HF snapshots may contain only component configs. Their repository directory
    # still identifies the exact version; arbitrary renamed folders do not.
    candidates = explicit or {
        variant
        for part in [
            path.name,
            *(parent.name for parent in path.parents if parent.name.startswith("models--")),
        ]
        if (variant := named_variant(part))
    }
    if len(candidates) != 1:
        raise ValueError(
            "Не удалось однозначно определить модель. Нужны метаданные MFLUX или папка с исходным именем HF-репозитория."
        )
    identity = VARIANTS[next(iter(candidates))]
    for class_name, supported in (
        (index.get("_class_name"), PIPELINES),
        (transformer.get("_class_name"), TRANSFORMERS),
    ):
        if class_name and (not isinstance(class_name, str) or supported.get(class_name) != identity.engine):
            raise ValueError("Архитектура checkpoint не соответствует поддерживаемой модели")
    if identity.engine == "mflux-flux" and "guidance_embeds" in transformer:
        if transformer["guidance_embeds"] != (identity.base_model != "schnell"):
            raise ValueError("Конфигурация FLUX не соответствует указанному варианту модели")
    return identity


def model_description(path: Path) -> dict:
    try:
        return {"recognized": True, **asdict(identify_model(path)), "error": None}
    except ValueError as error:
        return {
            "recognized": False,
            "engine": None,
            "base_model": None,
            "label": path.name,
            "error": str(error),
        }
