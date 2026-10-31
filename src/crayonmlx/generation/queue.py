"""One render worker, durable job snapshots and immutable per-job file locations."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from secrets import randbelow
from uuid import uuid4

from crayonmlx.engines.registry import validate_engine
from crayonmlx.models.catalog import resolve_model
from crayonmlx.models.identity import identify_model
from crayonmlx.schemas import GenerationRequest
from crayonmlx.storage.database import Database

logger = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GenerationQueue:
    def __init__(self, database: Database, engines: dict):
        self.database = database
        self.engines = engines
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crayonmlx-render")

    def submit(self, request: GenerationRequest, image) -> dict:
        request = request.model_copy(deep=True)
        settings = self.database.settings()
        model = resolve_model(Path(settings.models_dir), request.model)
        if not self.database.model_enabled(str(model)):
            raise ValueError("Модель выключена. Включите её в разделе «Модели».")
        identity = identify_model(model)
        request.preset.engine = identity.engine
        request.preset.base_model = identity.base_model
        engine = validate_engine(self.engines, request.preset)
        if request.preset.parameters.seed == -1:
            request.preset.parameters.seed = randbelow(2**32)
        identifier = uuid4().hex
        directory = Path(settings.output_dir) / identifier
        directory.mkdir(parents=True, exist_ok=False)
        source, output = directory / "source.png", directory / "result.png"
        image.save(source, format="PNG")
        snapshot = request.model_dump()
        snapshot["model_path"] = str(model)
        snapshot["prompt"] = request.preset.blocks.compose()
        metadata = json.dumps(snapshot, ensure_ascii=False, indent=2)
        (directory / "generation.json").write_text(metadata, encoding="utf-8")
        self.database.add_job(
            dict(
                id=identifier,
                created_at=now(),
                status="queued",
                request=metadata,
                source=str(source),
                output=str(output),
            )
        )
        self.executor.submit(self._run, identifier, engine, request.preset, model, source, output)
        return self.database.job(identifier)

    def _run(self, identifier, engine, preset, model, source, output):
        self.database.update_job(identifier, status="running", started_at=now())
        try:
            if not self.database.model_enabled(str(model)):
                raise ValueError("Модель была выключена до начала задания")
            execution = engine.render(preset, model, source, output) or {}
            if not output.is_file():
                raise RuntimeError("Движок не сохранил результат")
            metadata_path = output.with_name("generation.json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["execution"] = execution
            temporary = metadata_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(metadata_path)
            self.database.update_job(
                identifier, status="completed", finished_at=now(), execution=json.dumps(execution)
            )
        except Exception as error:
            logger.exception("Render failed: %s", identifier)
            self.database.update_job(identifier, status="failed", error=str(error), finished_at=now())

    def close(self):
        self.executor.shutdown(wait=True)
