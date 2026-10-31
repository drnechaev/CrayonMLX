"""Internal UI endpoints. Files are addressed by job IDs, never arbitrary paths."""

import io
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, ValidationError

from crayonmlx.engines.registry import validate_engine
from crayonmlx.models.catalog import list_models
from crayonmlx.schemas import GenerationRequest, Preset, Settings, StrictModel

router = APIRouter(prefix="/api")
MAX_UPLOAD = 20 * 1024 * 1024


class SettingsUpdate(Settings):
    hf_token: str | None = Field(default=None, max_length=1000)


class DownloadRequest(StrictModel):
    repo: str = Field(min_length=1, max_length=200)
    revision: str = Field(default="main", min_length=1, max_length=200)


def services(request: Request):
    return request.app.state.services


@router.get("/settings")
def get_settings(request: Request):
    state = services(request)
    return {
        **state.database.settings().model_dump(),
        "has_hf_token": bool(state.tokens.get()),
        "data_dir": str(state.root),
        "pending_data_dir": request.app.state.pending_data_dir,
    }


@router.put("/settings")
def put_settings(body: SettingsUpdate, request: Request):
    state = services(request)
    settings = Settings(
        models_dir=body.models_dir, output_dir=body.output_dir, model_idle_minutes=body.model_idle_minutes
    )
    # Probe paths before committing settings so access failures are visible immediately.
    for directory in (settings.models_dir, settings.output_dir):
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".crayonmlx-write-{uuid4().hex}"
        probe.touch()
        probe.unlink()
    if body.hf_token is not None:
        state.tokens.set(body.hf_token.strip())
    state.database.save_settings(settings)
    return get_settings(request)


@router.get("/engines")
def get_engines(request: Request):
    return [
        {
            "id": engine.id,
            "name": engine.name,
            "base_models": engine.base_models,
            "supports_strength": engine.supports_strength,
            "available": engine.available(),
        }
        for engine in services(request).engines.values()
    ]


@router.get("/models")
def get_models(request: Request):
    state = services(request)
    runtime = state.runtime.snapshot()
    return [
        {
            **model,
            "enabled": state.database.model_enabled(model["path"]),
            "runtime": runtime if runtime["model_path"] == model["path"] else {"phase": "unloaded"},
        }
        for model in list_models(Path(state.database.settings().models_dir))
    ]


@router.get("/downloads")
def get_downloads(request: Request):
    return services(request).downloads.list()


@router.post("/downloads", status_code=202)
def download_model(body: DownloadRequest, request: Request):
    state = services(request)
    return state.downloads.start(Path(state.database.settings().models_dir), body.repo, body.revision)


@router.get("/presets")
def get_presets(request: Request):
    return services(request).presets.list()


@router.post("/presets", status_code=201)
def create_preset(body: Preset, request: Request):
    state = services(request)
    validate_engine(state.engines, body)
    return state.presets.save(uuid4().hex, body)


@router.put("/presets/{identifier}")
def save_preset(identifier: str, body: Preset, request: Request):
    state = services(request)
    validate_engine(state.engines, body)
    if not state.presets.path(identifier).exists():
        raise HTTPException(404, "Пресет не найден")
    return state.presets.save(identifier, body)


@router.delete("/presets/{identifier}", status_code=204)
def delete_preset(identifier: str, request: Request):
    try:
        services(request).presets.delete(identifier)
    except FileNotFoundError:
        raise HTTPException(404, "Пресет не найден") from None


@router.post("/generations", status_code=202)
async def generate(request: Request, config: str = Form(...), image: UploadFile = File(...)):
    try:
        body = GenerationRequest.model_validate_json(config)
    except ValidationError as error:
        raise HTTPException(422, str(error)) from None
    contents = await image.read(MAX_UPLOAD + 1)
    await image.close()
    if len(contents) > MAX_UPLOAD:
        raise HTTPException(413, "Максимальный размер изображения — 20 МБ")
    try:
        with Image.open(io.BytesIO(contents)) as uploaded:
            if uploaded.width * uploaded.height > 25_000_000:
                raise HTTPException(413, "Максимальное разрешение исходника — 25 мегапикселей")
            normalized = ImageOps.exif_transpose(uploaded).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, "Не удалось прочитать изображение. Выберите PNG, JPEG или WebP.") from None
    return services(request).queue.submit(body, normalized)


@router.get("/generations")
def history(request: Request, limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    return services(request).database.jobs(limit, offset)


@router.get("/generations/{identifier}")
def job(identifier: str, request: Request):
    result = services(request).database.job(identifier)
    if not result:
        raise HTTPException(404, "Генерация не найдена")
    runtime = services(request).runtime.snapshot()
    if result["status"] == "running" and runtime.get("model_path") == result["request"].get("model_path"):
        result["progress"] = runtime
    return result


@router.get("/generations/{identifier}/{kind}")
def job_image(identifier: str, kind: str, request: Request):
    if kind not in ("source", "output"):
        raise HTTPException(404)
    result = job(identifier, request)
    if kind == "output" and result["status"] != "completed":
        raise HTTPException(404, "Результат пока не готов")
    path = Path(result[kind])
    if not path.is_file():
        raise HTTPException(404, "Файл был перемещён или удалён")
    return FileResponse(path, media_type="image/png", filename=f"crayonmlx-{identifier}-{kind}.png")
