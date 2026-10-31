"""An explicit internal-data transfer, applied after restarting the application."""

from fastapi import APIRouter, Request
from pydantic import Field

from crayonmlx.schemas import StrictModel
from crayonmlx.storage.location import prepare_location

router = APIRouter(prefix="/api")


class StorageLocation(StrictModel):
    data_dir: str = Field(min_length=1, max_length=4096)


@router.post("/storage/location")
def change_location(body: StorageLocation, request: Request):
    state = request.app.state.services
    target = prepare_location(state, body.data_dir)
    changed = target != state.root.resolve()
    if changed:
        # Freeze further writes so nothing can be lost between copying and restart.
        request.app.state.pending_data_dir = str(target)
    return {"data_dir": str(target), "restart_required": changed}
