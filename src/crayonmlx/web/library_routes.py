"""CRUD for prompt templates and render configurations; history has no write routes."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from crayonmlx.engines.registry import validate_engine
from crayonmlx.schemas import GenerationConfig, Preset, PromptBlocks, PromptTemplate

router = APIRouter(prefix="/api")


def update(repository, identifier, body):
    if not repository.path(identifier).exists():
        raise HTTPException(404, "Запись не найдена")
    return repository.save(identifier, body)


def remove(repository, identifier):
    try:
        repository.delete(identifier)
    except FileNotFoundError:
        raise HTTPException(404, "Запись не найдена") from None


def validate_config(request, body):
    validate_engine(
        request.app.state.services.engines,
        Preset(
            name=body.name,
            engine=body.engine,
            base_model=body.base_model,
            parameters=body.parameters,
            blocks=PromptBlocks(subject="Configuration validation"),
        ),
    )


@router.get("/prompt-templates")
def templates(request: Request):
    return request.app.state.services.prompts.list()


@router.post("/prompt-templates", status_code=201)
def create_template(body: PromptTemplate, request: Request):
    return request.app.state.services.prompts.save(uuid4().hex, body)


@router.put("/prompt-templates/{identifier}")
def update_template(identifier: str, body: PromptTemplate, request: Request):
    return update(request.app.state.services.prompts, identifier, body)


@router.delete("/prompt-templates/{identifier}", status_code=204)
def delete_template(identifier: str, request: Request):
    remove(request.app.state.services.prompts, identifier)


@router.get("/generation-configs")
def configs(request: Request):
    return request.app.state.services.configs.list()


@router.post("/generation-configs", status_code=201)
def create_config(body: GenerationConfig, request: Request):
    validate_config(request, body)
    return request.app.state.services.configs.save(uuid4().hex, body)


@router.put("/generation-configs/{identifier}")
def update_config(identifier: str, body: GenerationConfig, request: Request):
    validate_config(request, body)
    return update(request.app.state.services.configs, identifier, body)


@router.delete("/generation-configs/{identifier}", status_code=204)
def delete_config(identifier: str, request: Request):
    remove(request.app.state.services.configs, identifier)
