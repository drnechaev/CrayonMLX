"""macOS folder chooser for the local settings screen; no browser file uploads."""

import platform
import subprocess
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from crayonmlx.schemas import StrictModel

router = APIRouter(prefix="/api")
_dialog_lock = Lock()

# User-controlled paths travel as argv, never as executable AppleScript source.
_SCRIPT = """on run argv
    activate
    try
        set selectedFolder to choose folder with prompt (item 1 of argv) default location (POSIX file (item 2 of argv))
        return POSIX path of selectedFolder
    on error errorMessage number errorNumber
        if errorNumber is -128 then return ""
        error errorMessage number errorNumber
    end try
end run"""


class FolderRequest(StrictModel):
    target: Literal["models_dir", "output_dir", "data_dir"]
    current_path: str = Field(default="", max_length=4096)


def choose_folder(prompt: str, initial: str) -> str | None:
    if platform.system() != "Darwin":
        raise RuntimeError("Системный выбор папки доступен на macOS. Введите путь вручную.")
    directory = Path(initial).expanduser()
    if not directory.is_absolute():
        raise ValueError("Укажите абсолютный путь или очистите поле перед выбором папки")
    # A not-yet-created output directory starts the chooser at its existing parent.
    while not directory.is_dir():
        directory = directory.parent
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", _SCRIPT, prompt, str(directory)],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Время выбора папки истекло. Откройте диалог ещё раз.") from None
    except OSError:
        raise RuntimeError("Не удалось открыть системный диалог. Введите путь вручную.") from None
    if result.returncode:
        raise RuntimeError("Не удалось открыть системный диалог macOS. Введите путь вручную.")
    selected = result.stdout.rstrip("\r\n")
    if not selected:
        return None
    path = Path(selected)
    if not path.is_absolute() or not path.is_dir():
        raise RuntimeError("Выбранная папка недоступна. Выберите другую папку.")
    return str(path.resolve())


@router.post("/folders/select")
def select_folder(body: FolderRequest, request: Request):
    if not _dialog_lock.acquire(blocking=False):
        raise HTTPException(409, "Диалог выбора папки уже открыт")
    try:
        state = request.app.state.services
        initial = body.current_path or (
            str(state.root) if body.target == "data_dir" else getattr(state.database.settings(), body.target)
        )
        prompts = {
            "models_dir": "папку моделей",
            "output_dir": "папку результатов",
            "data_dir": "папку внутренних данных",
        }
        prompt = f"CrayonMLX — выберите {prompts[body.target]}"
        return {"path": choose_folder(prompt, initial)}
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from None
    finally:
        _dialog_lock.release()
