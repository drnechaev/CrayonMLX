"""One resident model with serialized access and an idle expiry policy."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock, Thread

from crayonmlx.engines.process import WorkerProcess


class ModelRuntime:
    def __init__(self, root, settings, worker_factory=WorkerProcess, clock=time.monotonic):
        self.root, self.settings, self.worker_factory, self.clock = root, settings, worker_factory, clock
        self.operation = Lock()
        self.state_lock = Lock()
        self.worker = None
        self.key = None
        self.state = {"phase": "unloaded", "model_path": None}
        self.last_used = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crayonmlx-model")
        self.stopped = Event()
        self.timer = Thread(target=self._idle_loop, daemon=True)
        self.timer.start()

    def _set(self, **values):
        with self.state_lock:
            self.state.update(values)

    def snapshot(self):
        with self.state_lock:
            result = dict(self.state)
            if self.worker:
                if self.worker.alive():
                    result.update(self.worker.snapshot())
                else:
                    result.update(phase="error", error="Процесс модели остановился")
            timeout = self.settings().model_idle_minutes
            result["idle_minutes"] = timeout
            result["unload_in_seconds"] = (
                max(0, round(timeout * 60 - (self.clock() - self.last_used)))
                if timeout is not None and self.last_used is not None and result["phase"] == "ready"
                else None
            )
            return result

    def _close_worker(self):
        with self.state_lock:
            worker = self.worker
            self.worker = None
            self.key = None
            self.last_used = None
            self.state = {"phase": "unloaded", "model_path": None}
        if worker:
            worker.close()

    def _ensure_loaded(self, engine, model, preset):
        key = (str(model), engine.id, preset.base_model, preset.parameters.quantize)
        if self.key == key and self.worker and self.worker.alive():
            return
        self._close_worker()
        self._set(phase="loading", model_path=str(model))
        worker = self.worker_factory(self.root)
        with self.state_lock:
            self.worker, self.key = worker, key
        worker.request(
            {
                "action": "load",
                "engine": engine.id,
                "base_model": preset.base_model,
                "quantize": preset.parameters.quantize,
                "model_path": str(model),
            }
        )
        self._set(phase="ready")

    def render(self, engine, preset, model, source, output):
        with self.operation:
            try:
                self._ensure_loaded(engine, model, preset)
                self._set(phase="preparing", output=str(output))
                self.worker.request(
                    {
                        "action": "render",
                        "preset": preset.model_dump(),
                        "source": str(source),
                        "output": str(output),
                    }
                )
                with self.state_lock:
                    self.last_used = self.clock()
                self._set(phase="ready")
                snapshot = self.snapshot()
                return {
                    key: snapshot.get(key)
                    for key in ("effective_quantize", "memory_peak_bytes", "elapsed_seconds", "total_steps")
                }
            except Exception as error:
                self._close_worker()
                self._set(phase="error", model_path=str(model), error=str(error))
                raise

    def load(self, engine, model, preset):
        if not self.operation.acquire(blocking=False):
            raise ValueError("Модель сейчас занята. Дождитесь завершения операции.")
        try:
            self._ensure_loaded(engine, model, preset)
            with self.state_lock:
                self.last_used = self.clock()
        except Exception as error:
            self._close_worker()
            self._set(phase="error", model_path=str(model), error=str(error))
        finally:
            self.operation.release()

    def request_load(self, engine, model, preset):
        if self.snapshot()["phase"] in {"loading", "preparing", "denoising", "decoding"}:
            raise ValueError("Модель сейчас занята")
        self.executor.submit(self.load, engine, model, preset)

    def unload(self):
        if not self.operation.acquire(blocking=False):
            raise ValueError("Дождитесь завершения загрузки или генерации")
        try:
            self._close_worker()
        finally:
            self.operation.release()

    def unload_when_idle(self, model_path):
        self.executor.submit(self._wait_unload, model_path)

    def _wait_unload(self, model_path=None):
        with self.operation:
            if model_path is None or (self.key and self.key[0] == model_path):
                self._close_worker()

    def expire_idle(self):
        if not self.operation.acquire(blocking=False):
            return
        try:
            timeout = self.settings().model_idle_minutes
            if (
                self.worker
                and self.last_used is not None
                and timeout is not None
                and self.clock() - self.last_used >= timeout * 60
            ):
                self._close_worker()
        finally:
            self.operation.release()

    def _idle_loop(self):
        while not self.stopped.wait(2):
            self.expire_idle()

    def close(self):
        self.stopped.set()
        self.timer.join()
        self.executor.shutdown(wait=True)
        self._wait_unload()
