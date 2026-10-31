"""Explicit background downloads; incomplete checkpoints stay out of the catalog."""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import uuid4

from huggingface_hub import snapshot_download
from huggingface_hub.utils import validate_repo_id

from crayonmlx.storage.secrets import TokenStore

logger = logging.getLogger(__name__)


class Downloads:
    def __init__(self, tokens: TokenStore):
        self.tokens = tokens
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crayonmlx-download")
        self.lock = Lock()
        self.items = {}

    def list(self) -> list[dict]:
        with self.lock:
            return [dict(item) for item in self.items.values()]

    def start(self, root: Path, repo: str, revision: str) -> dict:
        validate_repo_id(repo)
        root.mkdir(parents=True, exist_ok=True)
        destination = root / repo.replace("/", "--")
        if destination.exists():
            raise ValueError(
                "Такая папка уже существует. Используйте другую папку моделей или удалите её вручную."
            )
        with self.lock:
            if any(item["status"] in ("queued", "running") for item in self.items.values()):
                raise ValueError("Дождитесь завершения текущей загрузки")
            item = {"id": uuid4().hex, "repo": repo, "revision": revision, "status": "queued", "error": None}
            self.items[item["id"]] = item
        self.executor.submit(self._download, item["id"], destination, repo, revision, self.tokens.get())
        return dict(item)

    def _download(self, identifier, destination, repo, revision, token):
        partial = destination.parent / f".download-{destination.name}"
        with self.lock:
            self.items[identifier]["status"] = "running"
        try:
            snapshot_download(repo_id=repo, revision=revision, local_dir=partial, token=token or False)
            partial.rename(destination)
            with self.lock:
                self.items[identifier]["status"] = "completed"
        except Exception:
            # HF errors can contain request details: keep credentials out of UI and logs.
            logger.warning("Model download failed for %s", repo)
            with self.lock:
                self.items[identifier].update(
                    status="failed",
                    error="Загрузка не удалась. Проверьте repo, ревизию, доступ по токену, сеть и место на диске. Повторная загрузка продолжит скачивание.",
                )

    def close(self):
        self.executor.shutdown(wait=True)
