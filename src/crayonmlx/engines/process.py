"""Process transport, independent of model lifecycle and GPU imports."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4


class WorkerProcess:
    def __init__(self, root: Path):
        self.root = root / uuid4().hex
        self.root.mkdir(parents=True)
        self.log = (self.root / "worker.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "crayonmlx.engines.worker", str(self.root)],
            stdin=subprocess.PIPE,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        )

    def request(self, payload):
        identifier = uuid4().hex
        response = self.root / f"{identifier}.json"
        self.process.stdin.write(json.dumps({**payload, "request_id": identifier}) + "\n")
        self.process.stdin.flush()
        while not response.exists():
            if self.process.poll() is not None:
                tail = (self.root / "worker.log").read_text(encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(f"Процесс MLX остановился.\n{tail}")
            time.sleep(0.1)
        result = json.loads(response.read_text())
        response.unlink()
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return result

    def snapshot(self):
        path = self.root / "status.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def alive(self):
        return self.process.poll() is None

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.process.stdin:
            self.process.stdin.close()
        self.log.close()
