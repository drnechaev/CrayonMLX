"""Application composition: construct services once and close workers on shutdown."""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from crayonmlx.engines.registry import default_engines
from crayonmlx.generation.queue import GenerationQueue
from crayonmlx.models.downloads import Downloads
from crayonmlx.models.runtime import ModelRuntime
from crayonmlx.paths import data_directory
from crayonmlx.presets.library import ConfigRepository, PromptRepository
from crayonmlx.presets.repository import PresetRepository
from crayonmlx.storage.database import Database
from crayonmlx.storage.secrets import TokenStore
from crayonmlx.web.folders import router as folders_router
from crayonmlx.web.library_routes import router as library_router
from crayonmlx.web.model_routes import router as model_router
from crayonmlx.web.routes import router
from crayonmlx.web.storage_routes import router as storage_router


@dataclass
class Services:
    root: Path
    database: Database
    presets: PresetRepository
    prompts: PromptRepository
    configs: ConfigRepository
    tokens: TokenStore
    engines: dict
    queue: GenerationQueue
    downloads: Downloads
    runtime: ModelRuntime


def create_app(data_dir: Path | None = None, engines: dict | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        root = (data_dir or data_directory()).resolve()
        database = Database(root)
        runtime = ModelRuntime(root / "runtime", database.settings)
        registry = engines if engines is not None else default_engines(runtime)
        tokens = TokenStore(root)
        queue = GenerationQueue(database, registry)
        downloads = Downloads(tokens)
        app.state.services = Services(
            root,
            database,
            PresetRepository(root),
            PromptRepository(root),
            ConfigRepository(root),
            tokens,
            registry,
            queue,
            downloads,
            runtime,
        )
        try:
            yield
        finally:
            queue.close()
            runtime.close()
            downloads.close()

    app = FastAPI(title="CrayonMLX", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    write_lock = asyncio.Lock()
    app.state.pending_data_dir = None

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        # Local disk operations must not be triggered by a form on a remote website.
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if (origin and origin != str(request.base_url).rstrip("/")) or request.headers.get(
                "sec-fetch-site"
            ) == "cross-site":
                return JSONResponse(
                    {"detail": "Разрешены только запросы из локального интерфейса"}, status_code=403
                )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            async with write_lock:
                if app.state.pending_data_dir:
                    return JSONResponse(
                        {
                            "detail": "Папка данных перенесена. Перезапустите CrayonMLX, чтобы продолжить работу."
                        },
                        status_code=409,
                    )
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid_value(request, error):
        return JSONResponse({"detail": str(error)}, status_code=422)

    @app.exception_handler(OSError)
    async def filesystem_error(request, error):
        logging.getLogger(__name__).exception("Filesystem operation failed")
        return JSONResponse(
            {
                "detail": "Не удалось прочитать или записать файл. Проверьте путь, права доступа и свободное место."
            },
            status_code=400,
        )

    web = Path(__file__).parent / "web"
    app.include_router(router)
    app.include_router(library_router)
    app.include_router(folders_router)
    app.include_router(model_router)
    app.include_router(storage_router)
    app.mount("/static", StaticFiles(directory=web / "static"), name="static")

    @app.get("/")
    def index():
        return FileResponse(web / "index.html")

    return app
