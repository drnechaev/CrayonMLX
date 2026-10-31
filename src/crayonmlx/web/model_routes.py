"""Model availability and residency controls; no file deletion."""

from pathlib import Path

from fastapi import APIRouter, Request

from crayonmlx.engines.registry import validate_engine
from crayonmlx.models.catalog import resolve_model
from crayonmlx.models.identity import identify_model
from crayonmlx.schemas import Parameters, Preset, PromptBlocks, StrictModel

router = APIRouter(prefix="/api")


class ModelSelection(StrictModel):
    model: str


class ModelAvailability(ModelSelection):
    enabled: bool


class ModelLoad(ModelSelection):
    quantize: int | None = 4


def selected_path(request, model):
    return resolve_model(Path(request.app.state.services.database.settings().models_dir), model)


@router.get("/model-runtime")
def model_runtime(request: Request):
    return request.app.state.services.runtime.snapshot()


@router.post("/models/availability")
def availability(body: ModelAvailability, request: Request):
    state = request.app.state.services
    path = str(selected_path(request, body.model))
    state.database.set_model_enabled(path, body.enabled)
    if not body.enabled and state.runtime.snapshot()["model_path"] == path:
        state.runtime.unload_when_idle(path)
    return {"enabled": body.enabled}


@router.post("/models/load", status_code=202)
def load(body: ModelLoad, request: Request):
    state = request.app.state.services
    model = selected_path(request, body.model)
    if not state.database.model_enabled(str(model)):
        raise ValueError("Сначала включите модель")
    identity = identify_model(model)
    preset = Preset(
        name=identity.label,
        engine=identity.engine,
        base_model=identity.base_model,
        blocks=PromptBlocks(subject="Load model"),
        parameters=Parameters(quantize=body.quantize),
    )
    engine = validate_engine(state.engines, preset)
    if not engine.available():
        raise ValueError("Для загрузки нужен Mac Apple Silicon и MFLUX")
    state.runtime.request_load(engine, model, preset)
    return state.runtime.snapshot()


@router.post("/models/unload")
def unload(request: Request):
    request.app.state.services.runtime.unload()
    return {"phase": "unloaded"}
