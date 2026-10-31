"""Explicit registry: new engines implement the contract without changing the queue."""

from crayonmlx.engines.base import RenderEngine
from crayonmlx.engines.mflux import FluxEngine, QwenEditEngine
from crayonmlx.schemas import Preset


def default_engines(runtime=None) -> dict[str, RenderEngine]:
    return {engine.id: engine for engine in (FluxEngine(runtime), QwenEditEngine(runtime))}


def validate_engine(engines: dict[str, RenderEngine], preset: Preset) -> RenderEngine:
    engine = engines.get(preset.engine)
    if engine is None:
        raise ValueError("Неизвестный движок")
    if preset.base_model not in engine.base_models:
        raise ValueError("Базовая модель несовместима с выбранным движком")
    if not preset.blocks.compose():
        raise ValueError("Заполните хотя бы один блок промпта")
    return engine
